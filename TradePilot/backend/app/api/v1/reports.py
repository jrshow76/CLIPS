"""리포트 API 라우터.

`docs/13_api_requirements.md` §16 명세 구현.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.pagination import PageParams, page_params
from app.core.response import accepted_response, page_response, success_response
from app.schemas.report import (
    ExportRequestIn,
    ExportStatusOut,
    PnlReportOut,
    PnlSeriesItem,
    PositionReportItem,
    StrategyReportItem,
    TradeReportItem,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/pnl", summary="손익 리포트")
async def pnl(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    granularity: str = Query("D"),
):
    svc = ReportService(db)
    data = await svc.pnl_report(
        user.id,
        from_date=date.fromisoformat(from_),
        to_date=date.fromisoformat(to),
        granularity=granularity,
    )
    series = [PnlSeriesItem(**s) for s in data["series"]]
    return success_response(
        PnlReportOut(granularity=granularity, series=series, summary=data["summary"])
    )


@router.get("/positions", summary="종목별 손익")
async def positions(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
):
    svc = ReportService(db)
    rows = await svc.positions_report(
        user.id,
        from_date=date.fromisoformat(from_),
        to_date=date.fromisoformat(to),
    )
    items = [PositionReportItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.get("/trades", summary="거래 페이지")
async def trades(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    status: str | None = Query(None),
    code: str | None = Query(None),
):
    svc = ReportService(db)
    rows, total = await svc.trades_report(
        user.id,
        from_date=date.fromisoformat(from_),
        to_date=date.fromisoformat(to),
        status=status,
        code=code,
        offset=page.offset,
        limit=page.limit,
    )
    items = [TradeReportItem(**r) for r in rows]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.get("/strategies", summary="전략별 성과 비교")
async def strategies(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    strategy_ids: list[str] = Query(..., description="전략 public_id 목록"),
):
    svc = ReportService(db)
    rows = await svc.strategies_report(user.id, strategy_ids=strategy_ids)
    items = [StrategyReportItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.post("/export", summary="리포트 익스포트 요청", status_code=202)
async def export_request(
    payload: ExportRequestIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = ReportService(db)
    export_id = await svc.request_export(
        user.id,
        type_=payload.type,
        from_date=date.fromisoformat(payload.from_),
        to_date=date.fromisoformat(payload.to),
        fmt=payload.format,
    )
    return accepted_response(job_id=export_id, status="QUEUED", extra={"export_id": export_id})


@router.get("/export/{export_id}", summary="익스포트 상태")
async def export_status(
    export_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = ReportService(db)
    data = await svc.get_export_status(user.id, export_id)
    return success_response(ExportStatusOut(**data))
