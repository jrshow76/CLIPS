"""ML 예측 API 라우터.

`docs/13_api_requirements.md` §12 명세 구현.
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.response import accepted_response, success_response
from app.schemas.ml_prediction import (
    AccuracyOut,
    PredictionOut,
    PredictionPoint,
    RetrainIn,
    TrainingJobStatusOut,
)
from app.services.ml_prediction_service import MLPredictionService

router = APIRouter(prefix="/ml-predictions", tags=["ml-predictions"])


@router.get("/{code}", summary="단기 가격 예측")
async def get_predictions(
    code: str,
    db: AsyncSession = Depends(get_db),
    horizon: int = Query(5, ge=1, le=5),
):
    svc = MLPredictionService(db)
    rows = await svc.get_predictions(code, horizon=horizon)
    base = date.today()
    points = [
        PredictionPoint(
            date=(base + timedelta(days=r.horizon)),
            mean=r.pred_mean,
            lower=r.pred_lower,
            upper=r.pred_upper,
        )
        for r in rows
    ]
    return success_response(
        PredictionOut(
            code=code,
            predictions=points,
            model_version=(rows[0].model_version if rows else None),
        )
    )


@router.get("/{code}/accuracy", summary="ML 모델 정확도")
async def get_accuracy(
    code: str,
    db: AsyncSession = Depends(get_db),
    period: str = Query("M"),
):
    svc = MLPredictionService(db)
    data = await svc.get_accuracy(code, period=period)
    return success_response(AccuracyOut(**data))


@router.post("/retrain", summary="(ADMIN) LSTM 재학습 큐잉", status_code=202)
async def retrain(
    payload: RetrainIn,
    _admin=Depends(require_role("ROLE_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    svc = MLPredictionService(db)
    job_id = await svc.enqueue_retrain(codes=payload.codes, full=payload.full)
    return accepted_response(job_id=job_id, status="QUEUED")


@router.get("/jobs/{job_id}", summary="(ADMIN) 학습 잡 상태")
async def get_job_status(
    job_id: str,
    _admin=Depends(require_role("ROLE_ADMIN")),
):
    from app.workers.tasks.ml_tasks import get_job_status as _get_status

    status = _get_status(job_id)
    return success_response(
        TrainingJobStatusOut(
            job_id=job_id,
            status=status.get("status", "UNKNOWN"),
            started_at=None,
            finished_at=None,
        )
    )
