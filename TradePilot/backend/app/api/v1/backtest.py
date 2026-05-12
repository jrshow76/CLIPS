"""백테스트 API 라우터.

`docs/13_api_requirements.md` §11 명세 구현.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.pagination import PageParams, page_params
from app.core.response import accepted_response, page_response, success_response
from app.schemas.backtest import (
    BacktestJobCreateIn,
    BacktestProgressOut,
    BacktestResultOut,
    CompareIn,
    SaveResultIn,
    SavedResultItem,
)
from app.services.backtest_service import BacktestService

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/jobs", summary="백테스트 잡 생성", status_code=202)
async def create_job(
    payload: BacktestJobCreateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = BacktestService(db)
    run = await svc.enqueue(
        user_id=user.id,
        strategy_public_id=payload.strategy_id,
        universe=payload.universe,
        from_date=date.fromisoformat(payload.from_),
        to_date=date.fromisoformat(payload.to),
        initial_capital=payload.initial_capital,
        slippage=payload.slippage,
        fee_rate=payload.fee_rate,
    )
    return accepted_response(job_id=str(run.job_id), status=run.status)


@router.get("/jobs/{job_id}/progress", summary="백테스트 진행률")
async def get_progress(
    job_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = BacktestService(db)
    run = await svc.get_run(user_id=user.id, job_id=job_id)
    return success_response(
        BacktestProgressOut(
            job_id=str(run.job_id),
            status=run.status,
            percent=run.progress,
            eta_seconds=None,
        )
    )


@router.get("/jobs/{job_id}/result", summary="백테스트 결과")
async def get_result(
    job_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = BacktestService(db)
    data = await svc.get_result(user_id=user.id, job_id=job_id)
    return success_response(BacktestResultOut(**data))


@router.post("/jobs/{job_id}/cancel", summary="백테스트 취소")
async def cancel_job(
    job_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = BacktestService(db)
    run = await svc.cancel(user_id=user.id, job_id=job_id)
    return success_response({"job_id": str(run.job_id), "status": run.status})


@router.post("/results/{job_id}/save", summary="결과 저장")
async def save_result(
    job_id: str,
    payload: SaveResultIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = BacktestService(db)
    result = await svc.save_result(user_id=user.id, job_id=job_id, label=payload.label)
    return success_response({"saved": True, "label": result.label})


@router.get("/results", summary="저장된 결과 페이지")
async def list_saved(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
):
    svc = BacktestService(db)
    rows, total = await svc.list_saved(user.id, offset=page.offset, limit=page.limit)
    items = [
        SavedResultItem(
            run_id=res.run_id,
            job_id=str(run.job_id),
            label=res.label,
            cumulative_return=res.cumulative_return,
            annualized_return=res.annualized_return,
            mdd=res.mdd,
            sharpe=res.sharpe,
            saved_at=res.saved_at,
        )
        for res, run in rows
    ]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.post("/compare", summary="결과 비교")
async def compare(
    payload: CompareIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = BacktestService(db)
    data = await svc.compare(user_id=user.id, result_ids=payload.result_ids)
    return success_response(data)
