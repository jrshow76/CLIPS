"""주문 서비스 (유스케이스).

처리 흐름:
1. 멱등성 키 확인 (Redis 24h)
2. 종목 마스터 확인
3. 한도/리스크 검증 (TradeLimitService)
4. 시세 조회로 추정 가격 산정
5. Order ROW 생성 (NEW)
6. 라우터(SIM/LIVE) 호출
7. 결과 반영 (FILLED → Fill row + Position 갱신, ACCEPTED → 비동기 체결 이벤트 대기)
8. Redis 멱등성 캐시 저장

`docs/15_trading_policy.md` §1.3 책임 분리 다이어그램 준수.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import orjson
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.redis_client import get_redis
from app.domains.enums import OrderSide, OrderStatus, OrderType, TradeMode
from app.domains.ports.order_router_port import OrderRequest
from app.integrations.factory import get_market_data, get_order_router
from app.models.market import Stock
from app.models.trade import Fill, Order, Position
from app.models.user import User
from app.repositories.order_repository import (
    FillRepository,
    OrderRepository,
    PositionRepository,
    StockRepository,
)
from app.services.trade_limit_service import TradeLimitService

log = structlog.get_logger(__name__)


class OrderService:
    """주문 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.fills = FillRepository(db)
        self.positions = PositionRepository(db)
        self.stocks = StockRepository(db)
        self.limits = TradeLimitService(db)

    # ------------------------------------------------------------------
    # 주문 생성
    # ------------------------------------------------------------------
    async def create(
        self,
        *,
        user: User,
        trade_mode: str,
        code: str,
        side: str,
        order_type: str,
        qty: Decimal,
        price: Decimal | None,
        strategy_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Order:
        # 1) 멱등성 확인
        if idempotency_key:
            cached = await self._idempotency_get(user.id, idempotency_key)
            if cached:
                log.info("order_idempotent_hit", user_id=user.id, key=idempotency_key)
                existing = await self.orders.find_by_public_id(cached["order_public_id"])
                if existing:
                    return existing
            # DB에 동일 키 주문도 확인 (트랜잭션 격리)
            dup = await self.orders.find_by_idempotency_key(user.id, idempotency_key)
            if dup:
                return dup

        # 2) 종목 마스터 확인
        stock = await self.stocks.find_by_code(code)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")

        # 3) 시세 조회 (추정 체결가 계산용)
        market = get_market_data(trade_mode)
        try:
            snapshot = await market.get_snapshot(code)
            est_price = price or snapshot.price
        except Exception:
            est_price = price or Decimal("0")

        # 4) 한도 검증
        await self.limits.check_pre_order(
            user_id=user.id,
            trade_mode=trade_mode,
            side=side,
            stock_id=stock.id,
            qty=qty,
            est_price=est_price,
        )

        # 5) Order row (NEW)
        order = Order(
            user_id=user.id,
            stock_id=stock.id,
            trade_mode=trade_mode,
            side=side,
            order_type=order_type,
            qty=qty,
            price=price,
            status=OrderStatus.NEW.value,
            idempotency_key=idempotency_key,
        )
        await self.orders.add(order)
        await self.db.flush()  # public_id, id 확정

        # 6) 라우터 호출
        router = get_order_router(trade_mode)
        try:
            req = OrderRequest(
                order_id=order.id,
                user_id=user.id,
                stock_code=code,
                side=side,
                order_type=order_type,
                qty=qty,
                price=price,
                trade_mode=trade_mode,
                idempotency_key=idempotency_key,
            )
            result = await router.submit_order(req)
        except AppException:
            order.status = OrderStatus.REJECTED.value
            await self.db.commit()
            raise
        except Exception as e:
            log.exception("router_unknown_error", order_id=order.id)
            order.status = OrderStatus.REJECTED.value
            order.reject_reason = str(e)[:500]
            await self.db.commit()
            raise AppException("E0023", message="주문 처리 중 오류가 발생했습니다.") from e

        # 7) 결과 반영
        order.broker_order_no = result.broker_order_no
        order.status = result.status
        if result.reject_reason:
            order.reject_reason = result.reject_reason[:500]

        if result.status == OrderStatus.FILLED.value and result.filled_qty > 0:
            # 체결 row 생성
            fill = Fill(
                order_id=order.id,
                user_id=user.id,
                stock_id=stock.id,
                trade_mode=trade_mode,
                fill_qty=result.filled_qty,
                fill_price=result.avg_fill_price or est_price,
                fee=result.fee,
                tax=result.tax,
                slippage=result.slippage,
                filled_at=result.filled_at or datetime.now(tz=timezone.utc),
            )
            self.db.add(fill)
            order.filled_at = fill.filled_at
            # 포지션 갱신
            await self._apply_to_position(
                user_id=user.id,
                stock_id=stock.id,
                trade_mode=trade_mode,
                side=side,
                qty=result.filled_qty,
                price=result.avg_fill_price or est_price,
            )

        await self.db.commit()
        await self.db.refresh(order)

        # 8) 멱등성 캐시 저장
        if idempotency_key:
            await self._idempotency_set(
                user.id,
                idempotency_key,
                {"order_public_id": str(order.public_id), "status": order.status},
            )

        # 9) 체결 알림 발송 (실패해도 주문 흐름 차단 금지)
        if order.status == OrderStatus.FILLED.value:
            try:
                from app.services.notification_service import NotificationService

                fill_price = result.avg_fill_price or est_price
                amount = (fill_price or Decimal("0")) * (result.filled_qty or Decimal("0"))
                await NotificationService(self.db).send_execution_alert(
                    user=user,
                    stock_code=code,
                    stock_name=stock.name,
                    side=side,
                    trade_mode=trade_mode,
                    filled_qty=str(result.filled_qty),
                    filled_price=str(fill_price),
                    amount=str(amount),
                    fee=str(result.fee or 0),
                    order_public_id=str(order.public_id),
                )
            except Exception as _e:  # noqa: BLE001
                log.warning("execution_notify_failed", order_id=order.id, error=str(_e)[:200])

        log.info(
            "order_created",
            user_id=user.id,
            order_id=order.id,
            mode=trade_mode,
            side=side,
            qty=str(qty),
            status=order.status,
        )
        return order

    # ------------------------------------------------------------------
    # 주문 취소
    # ------------------------------------------------------------------
    async def cancel(
        self, *, user: User, trade_mode: str, order_public_id: str
    ) -> Order:
        order = await self.orders.find_by_public_id(order_public_id)
        if not order or order.user_id != user.id:
            raise AppException("E0062", message="주문을 찾을 수 없습니다.")
        if order.status in (OrderStatus.CANCELED.value, OrderStatus.FILLED.value):
            raise AppException(
                "E0022",
                message=f"이미 {order.status} 상태인 주문입니다.",
            )

        # 종목 정보
        stock = await self.stocks.get(order.stock_id)
        assert stock is not None

        router = get_order_router(trade_mode)
        result = await router.cancel_order(order.id, order.broker_order_no, stock.code)

        if result.accepted:
            order.status = OrderStatus.CANCELED.value
            order.canceled_at = datetime.now(tz=timezone.utc)
        else:
            raise AppException(
                "E0014",
                message="주문 취소에 실패했습니다.",
                details={"reason": result.reject_reason},
            )
        await self.db.commit()
        return order

    # ------------------------------------------------------------------
    # 주문 조회
    # ------------------------------------------------------------------
    async def get_one(self, *, user: User, order_public_id: str) -> Order:
        order = await self.orders.find_by_public_id(order_public_id)
        if not order or order.user_id != user.id:
            raise AppException("E0062")
        return order

    async def list_orders(
        self,
        *,
        user: User,
        status: str | None = None,
        code: str | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Order], int]:
        return await self.orders.list_for_user(
            user.id,
            status=status,
            code=code,
            from_dt=from_dt,
            to_dt=to_dt,
            offset=offset,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    async def _apply_to_position(
        self,
        *,
        user_id: int,
        stock_id: int,
        trade_mode: str,
        side: str,
        qty: Decimal,
        price: Decimal,
    ) -> None:
        """체결 결과를 포지션에 반영."""
        pos = await self.positions.find(user_id, stock_id, trade_mode)
        if side == OrderSide.BUY.value:
            if pos:
                new_qty = pos.qty + qty
                new_avg = ((pos.avg_price * pos.qty) + (price * qty)) / new_qty if new_qty else price
                pos.qty = new_qty
                pos.avg_price = new_avg.quantize(Decimal("0.01"))
            else:
                self.db.add(
                    Position(
                        user_id=user_id,
                        stock_id=stock_id,
                        trade_mode=trade_mode,
                        qty=qty,
                        avg_price=price,
                    )
                )
        else:  # SELL
            if not pos or pos.qty < qty:
                raise AppException("E0024", message="매도 가능 수량 부족 (체결 시점 검증).")
            realized = (price - pos.avg_price) * qty
            pos.qty = pos.qty - qty
            pos.realized_pnl = pos.realized_pnl + realized.quantize(Decimal("0.01"))

    async def _idempotency_get(self, user_id: int, key: str) -> dict[str, Any] | None:
        raw = await get_redis().get(f"idem:{user_id}:orders:{key}")
        return orjson.loads(raw) if raw else None

    async def _idempotency_set(self, user_id: int, key: str, value: dict[str, Any]) -> None:
        await get_redis().setex(
            f"idem:{user_id}:orders:{key}",
            settings.IDEMPOTENCY_TTL_SEC,
            orjson.dumps(value),
        )
