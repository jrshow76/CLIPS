"""주문 한도/리스크 검증 서비스 (Risk Guard).

`docs/15_trading_policy.md` §3, §4 정책 구현.
- 일일 매수 금액/건수
- 종목당 한도
- 보유 종목 수
- 일일 손실 한도
- 단일 주문 최대 수량
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.trade import TradeLimit
from app.repositories.order_repository import (
    OrderRepository,
    PositionRepository,
    TradeLimitRepository,
)

log = structlog.get_logger(__name__)


class TradeLimitService:
    """매매 한도 검증."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.limits = TradeLimitRepository(db)
        self.orders = OrderRepository(db)
        self.positions = PositionRepository(db)

    async def check_pre_order(
        self,
        *,
        user_id: int,
        trade_mode: str,
        side: str,
        stock_id: int,
        qty: Decimal,
        est_price: Decimal,
    ) -> None:
        """주문 직전 한도 검증.

        검증 실패 시 AppException(E0021) 발생.
        """
        limit: TradeLimit = await self.limits.find_or_default(user_id)

        # 1) 단일 주문 최대 수량
        if qty > Decimal(limit.single_order_max_qty):
            raise AppException(
                "E0021",
                message="단일 주문 최대 수량을 초과합니다.",
                details={
                    "limit": int(limit.single_order_max_qty),
                    "attempted": int(qty),
                },
            )

        est_amount = qty * est_price

        # 매수 한도 검증
        if side == "BUY":
            # 2) 종목당 매수 금액
            if est_amount > limit.per_stock_amount:
                raise AppException(
                    "E0021",
                    message="종목당 매수 한도를 초과합니다.",
                    details={
                        "limit": str(limit.per_stock_amount),
                        "attempted": str(est_amount),
                    },
                )

            # 3) 일일 매수 건수
            today = date.today()
            cnt = await self.orders.count_daily_buys(user_id, today)
            if cnt + 1 > limit.daily_buy_count:
                raise AppException(
                    "E0021",
                    message="일일 매수 건수 한도를 초과합니다.",
                    details={"limit": limit.daily_buy_count, "attempted": cnt + 1},
                )

            # 4) 일일 매수 금액
            daily_sum = await self.orders.sum_daily_buy_amount(user_id, today)
            if (daily_sum + est_amount) > limit.daily_buy_amount:
                raise AppException(
                    "E0021",
                    message="일일 매수 금액 한도를 초과합니다.",
                    details={
                        "limit": str(limit.daily_buy_amount),
                        "attempted": str(daily_sum + est_amount),
                    },
                )

            # 5) 보유 종목 수 (신규 진입 시)
            existing_position = await self.positions.find(user_id, stock_id, trade_mode)
            if not existing_position:
                pos_count = await self.positions.count_active(user_id, trade_mode)
                if pos_count + 1 > limit.max_positions:
                    raise AppException(
                        "E0021",
                        message="보유 종목 수 한도를 초과합니다.",
                        details={"limit": limit.max_positions, "current": pos_count},
                    )

        # 매도 검증
        if side == "SELL":
            position = await self.positions.find(user_id, stock_id, trade_mode)
            if not position or position.qty < qty:
                raise AppException(
                    "E0024",
                    message="매도 가능 수량이 부족합니다.",
                    details={"have": str(position.qty if position else 0), "want": str(qty)},
                )

        log.debug(
            "limit_check_passed",
            user_id=user_id,
            side=side,
            qty=str(qty),
            est_amount=str(est_amount),
        )
