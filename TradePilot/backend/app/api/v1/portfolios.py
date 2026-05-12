"""포트폴리오 API 라우터.

`docs/13_api_requirements.md` §10 명세 구현.
SIM/LIVE 모드 분기는 `X-Trade-Mode` 헤더로 처리한다.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, TradeModeDep
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.schemas.portfolio import (
    HistorySeriesPoint,
    PortfolioSummaryOut,
    PositionItem,
    RealizedPnlSummary,
)
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("/summary", summary="자산 요약")
async def summary(
    user: CurrentUser,
    mode: TradeModeDep,
    db: AsyncSession = Depends(get_db),
):
    svc = PortfolioService(db)
    data = await svc.summary(user.id, mode)
    return success_response(PortfolioSummaryOut(**data))


@router.get("/positions", summary="보유 포지션 페이지")
async def positions(
    user: CurrentUser,
    mode: TradeModeDep,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
):
    svc = PortfolioService(db)
    rows, total = await svc.positions(user.id, mode, offset=page.offset, limit=page.limit)
    items = [PositionItem(**r) for r in rows]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.get("/history", summary="자산 추이 시계열")
async def history(
    user: CurrentUser,
    mode: TradeModeDep,
    db: AsyncSession = Depends(get_db),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    granularity: str = Query("D", description="D|W|M"),
):
    svc = PortfolioService(db)
    data = await svc.history(
        user.id,
        mode,
        from_date=date.fromisoformat(from_),
        to_date=date.fromisoformat(to),
        granularity=granularity,
    )
    items = [HistorySeriesPoint(**r) for r in data]
    return success_response([i.model_dump() for i in items])


@router.get("/realized-pnl", summary="실현 손익 요약")
async def realized_pnl(
    user: CurrentUser,
    mode: TradeModeDep,
    db: AsyncSession = Depends(get_db),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
):
    svc = PortfolioService(db)
    data = await svc.realized_pnl(
        user.id,
        mode,
        from_date=date.fromisoformat(from_),
        to_date=date.fromisoformat(to),
    )
    return success_response(RealizedPnlSummary(**data))
