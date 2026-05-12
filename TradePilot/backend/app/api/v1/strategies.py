"""전략 API 라우터.

`docs/13_api_requirements.md` §8 명세 구현.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.models.trade import Strategy
from app.schemas.strategy import (
    StrategyActivateIn,
    StrategyCreateIn,
    StrategyOut,
    StrategyPerformanceOut,
    StrategyUpdateIn,
)
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/strategies", tags=["strategies"])


def _to_out(s: Strategy) -> StrategyOut:
    return StrategyOut(
        id=str(s.public_id),
        name=s.name,
        description=s.description,
        entry_rules=s.entry_rules or {},
        exit_rules=s.exit_rules or {},
        universe=s.universe or [],
        limits=s.limits or {},
        active=s.active,
        activated_at=s.activated_at,
        deactivated_at=s.deactivated_at,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("", summary="전략 목록")
async def list_strategies(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    active: bool | None = Query(None),
):
    svc = StrategyService(db)
    rows, total = await svc.list_for_user(
        user.id, active=active, offset=page.offset, limit=page.limit
    )
    items = [_to_out(s) for s in rows]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.post("", summary="전략 생성", status_code=201)
async def create_strategy(
    payload: StrategyCreateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = StrategyService(db)
    s = await svc.create(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        entry_rules=payload.entry_rules,
        exit_rules=payload.exit_rules,
        universe=payload.universe,
        limits=payload.limits,
    )
    return success_response(_to_out(s), http_status=201)


@router.get("/{strategy_id}", summary="전략 상세")
async def get_strategy(
    strategy_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = StrategyService(db)
    s = await svc.get_for_user(user.id, strategy_id)
    return success_response(_to_out(s))


@router.patch("/{strategy_id}", summary="전략 수정")
async def update_strategy(
    strategy_id: str,
    payload: StrategyUpdateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = StrategyService(db)
    s = await svc.update(
        user_id=user.id,
        public_id=strategy_id,
        name=payload.name,
        description=payload.description,
        entry_rules=payload.entry_rules,
        exit_rules=payload.exit_rules,
        universe=payload.universe,
        limits=payload.limits,
    )
    return success_response(_to_out(s))


@router.delete("/{strategy_id}", summary="전략 삭제")
async def delete_strategy(
    strategy_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = StrategyService(db)
    await svc.delete(user_id=user.id, public_id=strategy_id)
    return success_response({"deleted": True, "id": strategy_id})


@router.patch("/{strategy_id}/activate", summary="전략 활성/비활성")
async def activate_strategy(
    strategy_id: str,
    payload: StrategyActivateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = StrategyService(db)
    s = await svc.activate(
        user=user, public_id=strategy_id, active=payload.active, otp_token=payload.otp_token
    )
    return success_response(
        {
            "id": str(s.public_id),
            "active": s.active,
            "activated_at": s.activated_at.isoformat() if s.activated_at else None,
            "deactivated_at": s.deactivated_at.isoformat() if s.deactivated_at else None,
        }
    )


@router.get("/{strategy_id}/performance", summary="전략 성과")
async def performance(
    strategy_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    period: str = Query("M", description="W|M|Y"),
):
    """전략 성과 요약. v1: 거래 카운트 + mock 메트릭."""
    svc = StrategyService(db)
    s = await svc.get_for_user(user.id, strategy_id)
    # 실제 성과 집계는 OrderRepository / DailyPnl 기반 가능하지만,
    # v1.0은 mock으로 응답 (실서비스에서는 BackendSenior가 별도 집계 서비스 구현)
    return success_response(
        StrategyPerformanceOut(
            id=str(s.public_id),
            period=period,
            trades=0,
            win_rate=0.0,
            cumulative_return=0.0,
            mdd=0.0,
        )
    )
