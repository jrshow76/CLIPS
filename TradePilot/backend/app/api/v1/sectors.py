"""섹터 API 라우터.

`docs/13_api_requirements.md` §5 명세 구현.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.schemas.sector import (
    SectorFlowItem,
    SectorHeatmapOut,
    SectorOut,
    SectorRankingItem,
    SectorStockItem,
)
from app.services.sector_service import SectorService

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("", summary="섹터 마스터 리스트")
async def list_sectors(db: AsyncSession = Depends(get_db)):
    svc = SectorService(db)
    rows = await svc.list_all()
    items = [
        SectorOut(
            code=s.code,
            name=s.name,
            parent_code=s.parent_code,
            sort_order=s.sort_order,
        )
        for s in rows
    ]
    return success_response([i.model_dump() for i in items])


@router.get("/ranking", summary="섹터 등락률 랭킹")
async def ranking(
    db: AsyncSession = Depends(get_db),
    period: str = Query("D", description="D|W|M"),
    sort: str = Query("change_pct,desc"),
):
    svc = SectorService(db)
    rows = await svc.ranking(period=period, sort=sort)
    items = [SectorRankingItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.get("/flow", summary="섹터 자금 흐름")
async def flow(
    db: AsyncSession = Depends(get_db),
    period: str = Query("D"),
):
    svc = SectorService(db)
    rows = await svc.flow(period=period)
    items = [SectorFlowItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.get("/heatmap", summary="섹터 상관관계 히트맵")
async def heatmap(
    db: AsyncSession = Depends(get_db),
    window: int = Query(30, ge=5, le=180),
):
    svc = SectorService(db)
    data = await svc.heatmap(window=window)
    return success_response(SectorHeatmapOut(**data))


@router.get("/{code}/stocks", summary="섹터 내 종목 페이지")
async def stocks_in_sector(
    code: str,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
):
    svc = SectorService(db)
    rows, total = await svc.list_stocks(code, offset=page.offset, limit=page.limit)
    items = [SectorStockItem(**r) for r in rows]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)
