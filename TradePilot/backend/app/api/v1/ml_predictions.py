"""ML 예측 API 라우터.

`docs/13_api_requirements.md` §12 명세 구현.

엔드포인트:
    [Legacy]
    GET    /ml-predictions/{code}            - 회귀형 예측 조회 (구버전 호환)
    GET    /ml-predictions/{code}/accuracy   - 모델 정확도
    POST   /ml-predictions/retrain           - (ADMIN) 다종목 재학습
    GET    /ml-predictions/jobs/{job_id}     - 학습 잡 상태

    [신규: 3-class 분류 모델]
    POST   /ml/predict                       - 단건 추론 요청 (비동기)
    GET    /ml/predictions/{prediction_id}   - 추론 결과 폴링
    GET    /ml/predictions                   - 종목별 최근 예측 목록
    POST   /ml/train                         - (ADMIN) 학습 시작
    GET    /ml/train/{job_id}                - 학습 상태
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
    PredictionListItem,
    PredictionOut,
    PredictionPoint,
    PredictionResultOut,
    PredictRequestIn,
    RetrainIn,
    TrainingJobStatusOut,
    TrainRequestIn,
    TrainStatusOut,
)
from app.services.ml_prediction_service import MLPredictionService

router = APIRouter(prefix="/ml-predictions", tags=["ml-predictions"])
ml_router = APIRouter(prefix="/ml", tags=["ml"])


# ============================================================================
# Legacy 엔드포인트 (회귀형, 기존 호환)
# ============================================================================
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


# ============================================================================
# 신규 엔드포인트 (3-class 분류 모델)
# ============================================================================
@ml_router.post("/predict", summary="단건 추론 요청", status_code=202)
async def request_predict(
    payload: PredictRequestIn,
    db: AsyncSession = Depends(get_db),
):
    """비동기 추론 요청. prediction_id 반환 후 폴링."""
    svc = MLPredictionService(db)
    result = await svc.request_prediction(
        stock_code=payload.stock_code,
        horizon=payload.horizon,
    )
    return accepted_response(
        prediction_id=result["prediction_id"],
        status=result["status"],
        cached=result.get("cached", False),
    )


@ml_router.get("/predictions/{prediction_id}", summary="추론 결과 폴링")
async def get_predict_result(
    prediction_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = MLPredictionService(db)
    data = await svc.get_prediction(prediction_id)
    # PredictionResultOut 으로 정규화 (없는 키는 None)
    out = PredictionResultOut(
        prediction_id=prediction_id,
        status=str(data.get("status", "UNKNOWN")),
        direction=data.get("direction"),
        confidence=data.get("confidence"),
        prob_up=data.get("prob_up"),
        prob_flat=data.get("prob_flat"),
        prob_down=data.get("prob_down"),
        model_key=data.get("model_key"),
        asof_date=_parse_date(data.get("asof_date")),
        horizon=data.get("horizon_days") or data.get("horizon"),
        error=data.get("error"),
    )
    return success_response(out)


@ml_router.get("/predictions", summary="종목별 최근 추론 목록")
async def list_predictions(
    db: AsyncSession = Depends(get_db),
    stock_code: str = Query(..., min_length=4, max_length=10),
    horizon: int | None = Query(None, ge=1, le=5),
    limit: int = Query(20, ge=1, le=100),
):
    svc = MLPredictionService(db)
    rows = await svc.list_predictions(stock_code=stock_code, horizon=horizon, limit=limit)
    return success_response([PredictionListItem(**r) for r in rows])


@ml_router.post("/train", summary="(ADMIN) 학습 시작", status_code=202)
async def request_train(
    payload: TrainRequestIn,
    _admin=Depends(require_role("ROLE_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    svc = MLPredictionService(db)
    result = await svc.request_training(
        stock_code=payload.stock_code,
        horizon=payload.horizon,
        config_overrides=payload.config,
    )
    return accepted_response(job_id=result["job_id"], status=result["status"])


@ml_router.get("/train/{job_id}", summary="(ADMIN) 학습 상태")
async def get_train_status(
    job_id: str,
    _admin=Depends(require_role("ROLE_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    svc = MLPredictionService(db)
    data = await svc.get_training_status(job_id)
    out = TrainStatusOut(
        job_id=job_id,
        status=str(data.get("status", "UNKNOWN")),
        progress=data.get("progress"),
        stock_code=data.get("stock_code"),
        horizon=data.get("horizon"),
        best_val_loss=data.get("best_val_loss"),
        best_val_acc=data.get("best_val_acc"),
        best_val_f1=data.get("best_val_f1"),
        epochs_run=data.get("epochs_run"),
        duration_sec=data.get("duration_sec"),
        started_at=data.get("started_at"),
        finished_at=data.get("finished_at"),
        error=data.get("error"),
    )
    return success_response(out)


def _parse_date(val):
    """str/date → date 변환 (None pass-through)."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except ValueError:
        return None
