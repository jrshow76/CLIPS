"""시그널 API 라우터.

`docs/13_api_requirements.md` §7 명세 구현.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_role
from app.core.exceptions import AppException
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.models.trade import Strategy
from app.repositories.signal_repository import SignalRepository
from app.repositories.stock_repository import StockExtRepository
from app.schemas.signal import (
    SignalCountOut,
    SignalDetail,
    SignalItem,
    SignalTestIn,
)
from app.services.indicator_service import to_dataframe
from app.services.signal_management_service import SignalManagementService
from app.services.signal_service import SignalService
from app.services.stock_service import StockService

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", summary="시그널 목록")
async def list_signals(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    status: str | None = Query(None),
    strategy_id: str | None = Query(None),
    code: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    repo = SignalRepository(db)

    strategy_pk: int | None = None
    if strategy_id:
        s_row = (
            await db.execute(select(Strategy).where(Strategy.public_id == strategy_id))
        ).scalar_one_or_none()
        if s_row:
            strategy_pk = s_row.id

    from_dt = datetime.fromisoformat(from_) if from_ else None
    to_dt = datetime.fromisoformat(to) if to else None

    rows, total = await repo.list_for_user(
        user.id,
        status=status,
        strategy_id=strategy_pk,
        code=code,
        from_dt=from_dt,
        to_dt=to_dt,
        offset=page.offset,
        limit=page.limit,
    )
    items = [
        SignalItem(
            id=str(sig.public_id),
            code=stock.code,
            action=sig.action,  # type: ignore[arg-type]
            price=sig.trigger_price,
            confidence=sig.confidence,
            status=sig.status,  # type: ignore[arg-type]
            created_at=sig.generated_at,
        )
        for sig, stock in rows
    ]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.get("/active/count", summary="활성 시그널 카운트")
async def active_count(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = SignalManagementService(db)
    cnt = await svc.count_summary(user.id)
    return success_response(SignalCountOut(**cnt))


@router.post("/test", summary="(ADMIN) 강제 시그널 평가")
async def signal_test(
    payload: SignalTestIn,
    admin=Depends(require_role("ROLE_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """관리자: 특정 전략·종목 룰 평가를 강제로 실행해 시그널을 즉시 산출한다."""
    s_row = (
        await db.execute(select(Strategy).where(Strategy.public_id == payload.strategy_id))
    ).scalar_one_or_none()
    if not s_row:
        raise AppException("E0062", message="전략을 찾을 수 없습니다.")

    stock_repo = StockExtRepository(db)
    stock = await stock_repo.find_by_code(payload.code)
    if not stock:
        raise AppException("E0062", message="종목을 찾을 수 없습니다.")

    # 일봉 → 룰 평가
    stock_svc = StockService(db)
    candles = await stock_svc.get_candles(payload.code, interval="D", from_=None, to=None)
    df = to_dataframe(candles)
    sig_svc = SignalService(db)
    candidates = sig_svc.evaluate_rules(df)

    saved = []
    last_price = Decimal(str(df["close"].iloc[-1])) if len(df) else Decimal("0")
    for cand in candidates:
        sig = await sig_svc.persist_signal(
            user_id=admin.id,
            strategy_id=s_row.id,
            stock_id=stock.id,
            action=cand["action"],
            confidence=cand["confidence"],
            trigger_price=last_price,
            condition_trace={"rule": cand["code"], "trace": cand.get("trace", {})},
        )
        saved.append(str(sig.public_id))
    await db.commit()
    return success_response({"signals": saved, "evaluated": len(candidates)})


@router.get("/{signal_id}", summary="시그널 상세")
async def get_signal(
    signal_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SignalManagementService(db)
    sig, stock = await svc.get_one(user_id=user.id, signal_public_id=signal_id)
    return success_response(
        SignalDetail(
            id=str(sig.public_id),
            code=stock.code,
            strategy_id=str(sig.strategy_id) if sig.strategy_id else None,
            action=sig.action,  # type: ignore[arg-type]
            confidence=sig.confidence,
            trigger_price=sig.trigger_price,
            status=sig.status,  # type: ignore[arg-type]
            condition_trace=sig.condition_trace or {},
            generated_at=sig.generated_at,
            expires_at=sig.expires_at,
        )
    )


@router.post("/{signal_id}/ignore", summary="시그널 무시 처리")
async def ignore_signal(
    signal_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SignalManagementService(db)
    sig = await svc.ignore(user_id=user.id, signal_public_id=signal_id)
    return success_response({"id": str(sig.public_id), "status": sig.status})
