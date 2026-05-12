"""시장(지수) API 라우터.

`docs/13_api_requirements.md` §13 명세 구현.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response
from app.schemas.market import CalendarItem, IndexCandle, IndexItem, MarketStatusOut
from app.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/indices", summary="시장 지수")
async def indices(db: AsyncSession = Depends(get_db)):
    svc = MarketService(db)
    data = await svc.list_indices()
    items = [IndexItem(**d) for d in data]
    return success_response([i.model_dump() for i in items])


@router.get("/indices/{code}/candles", summary="지수 OHLCV")
async def index_candles(
    code: str,
    db: AsyncSession = Depends(get_db),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    svc = MarketService(db)
    rows = await svc.candles(
        code,
        from_date=date.fromisoformat(from_) if from_ else None,
        to_date=date.fromisoformat(to) if to else None,
    )
    items = [IndexCandle(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.get("/status", summary="장 운영 상태")
async def market_status(db: AsyncSession = Depends(get_db)):
    svc = MarketService(db)
    data = svc.market_status()
    return success_response(MarketStatusOut(**data))


@router.get("/calendar", summary="연간 휴장일")
async def calendar(
    db: AsyncSession = Depends(get_db),
    year: int = Query(..., ge=2024, le=2030),
):
    svc = MarketService(db)
    rows = svc.calendar(year)
    items = [CalendarItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])
