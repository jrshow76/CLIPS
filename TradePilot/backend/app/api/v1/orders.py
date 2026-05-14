"""주문 API 라우터.

`docs/13_api_requirements.md` §9, `docs/24_api_response_spec.md` §17 명세.
- 모든 주문 변경 API는 X-Trade-Mode 헤더 필수
- POST /orders는 X-Idempotency-Key 권장
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, TradeModeDep, get_idempotency_key
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.models.market import Stock
from app.models.trade import Order
from app.schemas.order import (
    CancelOrderResponse,
    LiquidateAllRequest,
    LiquidateAllResponse,
    OrderCreateIn,
    OrderListItem,
    OrderOut,
)
from app.services.kill_switch_service import KillSwitchService
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


# ---------------------------------------------------------------------------
# 도우미: ORM Order → OrderOut (코드 매핑용)
# ---------------------------------------------------------------------------
async def _to_out(db: AsyncSession, order: Order) -> OrderOut:
    stock = await db.get(Stock, order.stock_id)
    return OrderOut(
        id=str(order.public_id),
        code=stock.code if stock else "",
        side=order.side,  # type: ignore[arg-type]
        order_type=order.order_type,  # type: ignore[arg-type]
        qty=order.qty,
        price=order.price,
        status=order.status,  # type: ignore[arg-type]
        mode=order.trade_mode,  # type: ignore[arg-type]
        broker_order_no=order.broker_order_no,
        reject_reason=order.reject_reason,
        created_at=order.created_at,
        filled_at=order.filled_at,
    )


# ---------------------------------------------------------------------------
# POST /orders
# ---------------------------------------------------------------------------
@router.post("", summary="주문 생성", status_code=201)
async def create_order(
    payload: OrderCreateIn,
    user: CurrentUser,
    mode: TradeModeDep,
    idempotency_key: Annotated[str | None, Depends(get_idempotency_key)] = None,
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    order = await svc.create(
        user=user,
        trade_mode=mode,
        code=payload.code,
        side=payload.side,
        order_type=payload.order_type,
        qty=Decimal(payload.qty),
        price=payload.price,
        strategy_id=payload.strategy_id,
        idempotency_key=idempotency_key,
    )
    out = await _to_out(db, order)
    return success_response(out, http_status=201)


# ---------------------------------------------------------------------------
# GET /orders
# ---------------------------------------------------------------------------
@router.get("", summary="주문 목록")
async def list_orders(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    status: str | None = Query(None),
    code: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to_: str | None = Query(None, alias="to"),
):
    svc = OrderService(db)
    from_dt = datetime.fromisoformat(from_) if from_ else None
    to_dt = datetime.fromisoformat(to_) if to_ else None
    rows, total = await svc.list_orders(
        user=user,
        status=status,
        code=code,
        from_dt=from_dt,
        to_dt=to_dt,
        offset=page.offset,
        limit=page.limit,
    )
    items: list[OrderListItem] = []
    for o in rows:
        stock = await db.get(Stock, o.stock_id)
        items.append(
            OrderListItem(
                id=str(o.public_id),
                code=stock.code if stock else "",
                side=o.side,  # type: ignore[arg-type]
                order_type=o.order_type,  # type: ignore[arg-type]
                qty=o.qty,
                price=o.price,
                status=o.status,  # type: ignore[arg-type]
                mode=o.trade_mode,  # type: ignore[arg-type]
                created_at=o.created_at,
                filled_at=o.filled_at,
            )
        )
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


# ---------------------------------------------------------------------------
# GET /orders/{id}
# ---------------------------------------------------------------------------
@router.get("/{order_id}", summary="주문 상세")
async def get_order(
    order_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    order = await svc.get_one(user=user, order_public_id=order_id)
    out = await _to_out(db, order)
    return success_response(out)


# ---------------------------------------------------------------------------
# POST /orders/{id}/cancel
# ---------------------------------------------------------------------------
@router.post("/{order_id}/cancel", summary="주문 취소")
async def cancel_order(
    order_id: str,
    user: CurrentUser,
    mode: TradeModeDep,
    db: AsyncSession = Depends(get_db),
):
    svc = OrderService(db)
    order = await svc.cancel(user=user, trade_mode=mode, order_public_id=order_id)
    return success_response(
        CancelOrderResponse(
            id=str(order.public_id),
            status=order.status,  # type: ignore[arg-type]
            canceled=order.status == "CANCELED",
        )
    )


# ---------------------------------------------------------------------------
# POST /orders/liquidate-all
# ---------------------------------------------------------------------------
@router.post("/liquidate-all", summary="전 보유 청산 (Kill Switch)")
async def liquidate_all(
    payload: LiquidateAllRequest,
    user: CurrentUser,
    mode: TradeModeDep,
    db: AsyncSession = Depends(get_db),
):
    """비상정지 (Kill Switch).

    SEC-003(GATE-1): 라우터(SIM/LIVE)의 cancel_order를 실제 호출하여 미체결을
    정리한다. LIVE 모드는 게이트웨이에 X-Idempotency-Key 포함 cancel_order 호출.
    """
    svc = KillSwitchService(db)
    result = await svc.trigger(
        user_id=user.id,
        trade_mode=mode,
        trigger_type="USER",
        trigger_source="USER",
        reason=payload.reason,
    )
    return success_response(
        LiquidateAllResponse(
            processed=result["canceled_orders"],
            failed=result["failed"],
        )
    )
