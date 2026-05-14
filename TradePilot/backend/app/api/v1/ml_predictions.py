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
    EnsembleContribution,
    EnsembleResultOut,
    ModelCatalogItem,
    ModelCatalogOut,
    ModelComparisonOut,
    PredictionListItem,
    PredictionOut,
    PredictionPoint,
    PredictionResultOut,
    PredictRequestIn,
    RetrainIn,
    TrainGlobalIn,
    TrainingJobStatusOut,
    TrainRequestIn,
    TrainSectorIn,
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
@ml_router.post("/predict", summary="단건 추론 요청")
async def request_predict(
    payload: PredictRequestIn,
    db: AsyncSession = Depends(get_db),
):
    """추론 요청.

    - `ensemble=True` (기본): 개별/섹터/글로벌 모델을 가중 평균하여 즉시 반환.
    - `ensemble=False`: 기존 비동기 단일 모델 추론 (prediction_id 반환).
    """
    if payload.ensemble:
        result = await _run_ensemble_async(
            stock_code=payload.stock_code,
            horizon=payload.horizon,
            sector_code=payload.sector_code,
        )
        return success_response(result)

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


async def _run_ensemble_async(
    stock_code: str, horizon: int, sector_code: str | None
) -> EnsembleResultOut:
    """앙상블 추론을 비동기 컨텍스트에서 호출 (sync 코어 → run_in_threadpool)."""
    from fastapi.concurrency import run_in_threadpool

    return await run_in_threadpool(
        _ensemble_sync, stock_code, horizon, sector_code
    )


def _ensemble_sync(
    stock_code: str, horizon: int, sector_code: str | None
) -> EnsembleResultOut:
    """앙상블 동기 코어 (워커 헬퍼 재사용)."""
    from app.services.ml_engine import predict_ensemble
    from app.workers.tasks.ml_tasks import _get_stock_sector, _load_ohlcv

    ohlcv = _load_ohlcv(stock_code, lookback_days_min=200)
    if ohlcv.empty:
        raise RuntimeError(f"OHLCV 데이터 없음: {stock_code}")

    sec = sector_code or _get_stock_sector(stock_code)
    result = predict_ensemble(
        ohlcv=ohlcv,
        stock_code=stock_code,
        horizon=horizon,
        sector_code=sec,
    )
    contributions = {
        k: EnsembleContribution(**v) for k, v in result.contributions.items()
    }
    return EnsembleResultOut(
        stock_code=stock_code,
        horizon=horizon,
        direction=result.direction,
        confidence=result.confidence,
        prob_up=result.prob_up,
        prob_flat=result.prob_flat,
        prob_down=result.prob_down,
        asof_date=result.asof_date,
        used_kinds=result.used_kinds,
        contributions=contributions,
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


# ============================================================================
# 멀티 모델: 카탈로그 / 학습 / 비교
# ============================================================================
@ml_router.get("/models", summary="모델 카탈로그", response_model=None)
async def list_model_catalog():
    """저장된 모델 카탈로그를 종류별로 반환.

    응답 키: individual / sector / global
    """
    from fastapi.concurrency import run_in_threadpool

    grouped = await run_in_threadpool(_list_models_sync)
    return success_response(grouped)


def _list_models_sync() -> ModelCatalogOut:
    from app.services.ml_engine import list_available_models

    grouped = list_available_models()

    def _to_item(d: dict) -> ModelCatalogItem:
        return ModelCatalogItem(
            model_key=d["model_key"],
            kind=d["kind"],
            stock_code=d.get("stock_code") or None,
            identifier=d.get("identifier") or None,
            horizon_days=int(d.get("horizon_days", 0)),
            lookback_days=int(d.get("lookback_days", 0)),
            features=list(d.get("features", [])),
            best_val_acc=d.get("best_val_acc"),
            best_val_f1=d.get("best_val_f1"),
            trained_at=d.get("trained_at"),
            model_param_count=d.get("model_param_count"),
            num_stocks=int(d.get("num_stocks", 1)),
        )

    return ModelCatalogOut(
        individual=[_to_item(d) for d in grouped.get("INDIVIDUAL", [])],
        sector=[_to_item(d) for d in grouped.get("SECTOR", [])],
        **{"global": [_to_item(d) for d in grouped.get("GLOBAL", [])]},
    )


@ml_router.post(
    "/train/sector/{sector_code}",
    summary="(ADMIN) 섹터 모델 학습 시작",
    status_code=202,
)
async def request_train_sector(
    sector_code: str,
    payload: TrainSectorIn,
    _admin=Depends(require_role("ROLE_ADMIN")),
):
    """섹터 모델 학습 큐잉."""
    from uuid import uuid4

    from app.workers.tasks.ml_tasks import train_sector as train_sector_task

    job_id = f"sector-{sector_code}-{payload.horizon}-{uuid4().hex[:8]}"

    # stock_codes 가 없으면 DB 에서 조회 (워커가 처리)
    codes = payload.stock_codes
    if not codes:
        codes = _safe_sector_stock_codes(sector_code)
    if not codes:
        return accepted_response(
            job_id=job_id,
            status="REJECTED",
            reason=f"섹터 {sector_code} 종목을 찾지 못했습니다",
        )

    train_sector_task.apply_async(
        kwargs={
            "job_id": job_id,
            "sector_code": sector_code,
            "stock_codes": codes,
            "horizon": payload.horizon,
            "config_overrides": payload.config or {},
        },
        task_id=job_id,
    )
    return accepted_response(job_id=job_id, status="QUEUED", n_stocks=len(codes))


@ml_router.post(
    "/train/global",
    summary="(ADMIN) 글로벌 모델 학습 시작",
    status_code=202,
)
async def request_train_global(
    payload: TrainGlobalIn,
    _admin=Depends(require_role("ROLE_ADMIN")),
):
    """글로벌 모델 학습 큐잉."""
    from uuid import uuid4

    from app.workers.tasks.ml_tasks import train_global as train_global_task

    job_id = f"global-{payload.horizon}-{uuid4().hex[:8]}"
    train_global_task.apply_async(
        kwargs={
            "job_id": job_id,
            "stock_codes": payload.stock_codes,
            "horizon": payload.horizon,
            "config_overrides": payload.config or {},
        },
        task_id=job_id,
    )
    return accepted_response(job_id=job_id, status="QUEUED")


@ml_router.get(
    "/comparison/{stock_code}",
    summary="모델별 예측 비교 (디버그)",
    response_model=None,
)
async def get_model_comparison(
    stock_code: str,
    horizon: int = Query(1, ge=1, le=5),
    sector_code: str | None = Query(None),
):
    """개별/섹터/글로벌/앙상블 결과를 모두 반환 (디버그용)."""
    from fastapi.concurrency import run_in_threadpool

    data = await run_in_threadpool(
        _model_comparison_sync, stock_code, horizon, sector_code
    )
    return success_response(data)


def _model_comparison_sync(
    stock_code: str, horizon: int, sector_code: str | None
) -> ModelComparisonOut:
    """모델별 예측 동기 코어."""
    from app.services.ml_engine.predictor import (
        _predict_global_probs,
        _predict_individual_probs,
        _predict_sector_probs,
    )
    from app.workers.tasks.ml_tasks import _get_stock_sector, _load_ohlcv

    ohlcv = _load_ohlcv(stock_code, lookback_days_min=200)
    sec = sector_code or _get_stock_sector(stock_code)

    out = ModelComparisonOut(stock_code=stock_code, horizon=horizon)

    ind = _predict_individual_probs(ohlcv, stock_code, horizon)
    if ind is not None:
        probs, key = ind
        out.individual = EnsembleContribution(
            model_key=key,
            prob_down=float(probs[0]),
            prob_flat=float(probs[1]),
            prob_up=float(probs[2]),
            weight=0.0,
        )

    if sec:
        sec_res = _predict_sector_probs(ohlcv, stock_code, sec, horizon)
        if sec_res is not None:
            probs, key = sec_res
            out.sector = EnsembleContribution(
                model_key=key,
                prob_down=float(probs[0]),
                prob_flat=float(probs[1]),
                prob_up=float(probs[2]),
                weight=0.0,
            )

    glo = _predict_global_probs(ohlcv, stock_code, horizon)
    if glo is not None:
        probs, key = glo
        setattr(out, "global_", EnsembleContribution(
            model_key=key,
            prob_down=float(probs[0]),
            prob_flat=float(probs[1]),
            prob_up=float(probs[2]),
            weight=0.0,
        ))

    # 앙상블도 계산
    try:
        out.ensemble = _ensemble_sync(stock_code, horizon, sec)
    except Exception:
        out.ensemble = None
    return out


def _safe_sector_stock_codes(sector_code: str) -> list[str]:
    """섹터 코드 → 종목 코드 리스트 (실패 시 빈 리스트)."""
    try:
        from sqlalchemy import create_engine, text

        from app.core.config import settings

        url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine = create_engine(url, pool_pre_ping=True)
        sql = text(
            """
            SELECT s.code FROM tp_market.stocks s
            JOIN tp_market.sectors sec ON sec.id = s.sector_id
            WHERE sec.code = :sector AND s.status = 'LISTED'
            ORDER BY s.code
            """
        )
        with engine.connect() as conn:
            rows = conn.execute(sql, {"sector": sector_code}).fetchall()
        engine.dispose()
        return [str(r[0]) for r in rows]
    except Exception:
        import os
        if os.getenv("ML_USE_SYNTHETIC", "false").lower() == "true":
            return [f"{sector_code}{i:03d}" for i in range(5)]
        return []
