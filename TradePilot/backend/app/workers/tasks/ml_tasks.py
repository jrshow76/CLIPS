"""ML 워커 태스크.

태스크:
    - ml.predict          : 단건 추론 (캐시 → DB INSERT → Redis result 저장)
    - ml.train            : 단일 종목/호라이즌 학습
    - ml.batch_predict    : 모든 활성 종목 일괄 추론 (스케줄러용)
    - ml.retrain          : (legacy) 다종목 일괄 학습 - 하위 호환

진행률/결과는 Redis 에 저장:
    ml:pred:result:{prediction_id}   = JSON (DONE 시)
    ml:train:status:{job_id}         = JSON (RUNNING/DONE/FAILED + metrics)

DB 접근은 동기 세션을 사용한다 (Celery 워커 컨텍스트). 비동기 ORM 을 만들기보다는
psycopg2 등을 통한 동기 사용이 운영상 단순하다. 이 프로젝트의 다른 워커
(예: backtest_tasks) 와 동일하게 핵심 동작은 사용 가능한 환경에서만 처리하고,
DB/torch 미가용 환경에서는 우아하게 SKIP 한다.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)

# 메모리 기반 잡 상태 캐시 (legacy, retrain_lstm 용)
_JOB_CACHE: dict[str, dict[str, Any]] = {}


# ============================================================================
# 단건 추론
# ============================================================================
@shared_task(name="ml.predict", queue="ml", bind=True, max_retries=2)
def predict_one(
    self,
    prediction_id: str,
    stock_code: str,
    horizon: int,
    user_id: int | None = None,
) -> dict[str, Any]:
    """단건 추론.

    1) OHLCV 로드 (DB 우선, ML_USE_SYNTHETIC=true 면 합성)
    2) ml_engine.predict_from_ohlcv 호출
    3) ml_predictions 테이블 INSERT
    4) Redis ml:pred:result:{prediction_id} 저장
    """
    started = datetime.now(UTC)
    log.info(
        "ml_predict_task_started",
        prediction_id=prediction_id,
        stock_code=stock_code,
        horizon=horizon,
    )
    try:
        result_dict = _run_predict(stock_code=stock_code, horizon=horizon)
        result_dict.update(
            {
                "prediction_id": prediction_id,
                "status": "DONE",
                "stock_code": stock_code,
                "horizon": horizon,
                "user_id": user_id,
                "started_at": started.isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
            }
        )
        _store_result(prediction_id, result_dict)
        # 30분 캐시
        _set_cache(_cache_key(stock_code, horizon, date.today()), result_dict)
        log.info("ml_predict_task_done", prediction_id=prediction_id)
        return result_dict
    except Exception as e:  # pragma: no cover - retry 경로
        log.warning(
            "ml_predict_task_failed",
            prediction_id=prediction_id,
            error=str(e),
        )
        failure = {
            "prediction_id": prediction_id,
            "status": "FAILED",
            "error": str(e),
            "stock_code": stock_code,
            "horizon": horizon,
        }
        _store_result(prediction_id, failure)
        try:
            raise self.retry(exc=e, countdown=10) from e
        except Exception:
            return failure


# ============================================================================
# 학습
# ============================================================================
@shared_task(
    name="ml.train",
    queue="ml",
    bind=True,
    max_retries=1,
    time_limit=3600,  # 1시간 제한
)
def train_one(
    self,
    job_id: str,
    stock_code: str,
    horizon: int = 1,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """단일 종목/호라이즌 학습."""
    started = datetime.now(UTC)
    _set_train_status(job_id, {
        "job_id": job_id,
        "status": "RUNNING",
        "stock_code": stock_code,
        "horizon": horizon,
        "progress": 0,
        "started_at": started.isoformat(),
    })

    log.info("ml_train_task_started", job_id=job_id, stock_code=stock_code, horizon=horizon)
    try:
        result = _run_train(
            job_id=job_id,
            stock_code=stock_code,
            horizon=horizon,
            config_overrides=config_overrides or {},
        )
        result.update(
            {
                "job_id": job_id,
                "status": "DONE",
                "started_at": started.isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
            }
        )
        _set_train_status(job_id, result)
        log.info("ml_train_task_done", job_id=job_id, **{k: result.get(k) for k in ("best_val_loss", "best_val_acc", "epochs_run")})
        return result
    except Exception as e:  # pragma: no cover
        log.warning("ml_train_task_failed", job_id=job_id, error=str(e))
        failure = {
            "job_id": job_id,
            "status": "FAILED",
            "error": str(e),
            "stock_code": stock_code,
            "horizon": horizon,
        }
        _set_train_status(job_id, failure)
        return failure


# ============================================================================
# 일괄 추론 (스케줄러용)
# ============================================================================
@shared_task(name="ml.batch_predict", queue="ml", bind=True)
def batch_predict(self, horizons: list[int] | None = None) -> dict[str, Any]:
    """모든 활성 종목 일괄 추론.

    `tp_market.stocks.status = 'LISTED'` 에 한해 학습된 모델이 존재하는 종목만 추론.
    """
    horizons = horizons or [1]
    results: dict[str, Any] = {"horizons": horizons, "processed": 0, "skipped": 0, "failed": 0}

    try:
        codes = _list_active_codes()
    except Exception as e:
        log.warning("ml_batch_predict_load_codes_failed", error=str(e))
        return {**results, "status": "FAILED", "error": str(e)}

    log.info("ml_batch_predict_started", n_codes=len(codes), horizons=horizons)
    for code in codes:
        for h in horizons:
            if not _model_exists(code, h):
                results["skipped"] += 1
                continue
            try:
                _run_predict(stock_code=code, horizon=h)
                results["processed"] += 1
            except Exception as e:
                log.warning("ml_batch_predict_failed", code=code, horizon=h, error=str(e))
                results["failed"] += 1

    results["status"] = "DONE"
    log.info("ml_batch_predict_done", **results)
    return results


# ============================================================================
# Legacy: 기존 retrain 태스크 (하위 호환)
# ============================================================================
@shared_task(name="ml.retrain", queue="ml", bind=True)
def retrain_lstm(self, job_id: str, codes: list[str], full: bool) -> dict[str, Any]:
    """다종목 LSTM 모델 재학습. 종목별로 train_one 을 fan-out 한다."""
    log.info("ml_retrain_started", job_id=job_id, full=full, codes=codes)
    _JOB_CACHE[job_id] = {"status": "RUNNING"}

    child_jobs: list[dict[str, Any]] = []
    for code in codes:
        for horizon in (1, 3, 5):
            try:
                child_id = f"{job_id}-{code}-{horizon}"
                train_one.apply_async(
                    kwargs={"job_id": child_id, "stock_code": code, "horizon": horizon},
                    task_id=child_id,
                )
                child_jobs.append({"code": code, "horizon": horizon, "child_id": child_id})
            except Exception as e:
                log.warning("ml_retrain_child_enqueue_failed", code=code, error=str(e))

    _JOB_CACHE[job_id] = {"status": "DONE", "children": child_jobs}
    log.info("ml_retrain_done", job_id=job_id, n_children=len(child_jobs))
    return {"job_id": job_id, "status": "DONE", "codes": codes, "full": full, "children": child_jobs}


def get_job_status(job_id: str) -> dict[str, Any]:
    """학습 잡 상태 조회 (legacy + 신규)."""
    if job_id in _JOB_CACHE:
        return _JOB_CACHE[job_id]
    # Redis 에서 신규 train 상태 조회
    try:
        import redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        raw = r.get(f"ml:train:status:{job_id}")
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return {"status": "UNKNOWN"}


# ============================================================================
# 내부 헬퍼: 동기 DB / Redis / ml_engine 호출
# ============================================================================
def _run_predict(stock_code: str, horizon: int) -> dict[str, Any]:
    """동기 추론 코어. DB 가 없으면 합성 시계열로 동작 (ML_USE_SYNTHETIC=true)."""
    from app.services.ml_engine import (
        predict_from_ohlcv,
        predictions_to_ml_record,
    )

    ohlcv = _load_ohlcv(stock_code, lookback_days_min=200)
    if ohlcv.empty:
        raise RuntimeError(f"OHLCV 데이터 없음: {stock_code}")

    meta_path = _meta_path(stock_code, horizon)
    config = _load_config_from_meta(meta_path, stock_code, horizon)
    pred = predict_from_ohlcv(ohlcv, config)
    record = predictions_to_ml_record(pred, last_close=float(ohlcv["close"].iloc[-1]))

    # DB 저장 (가능한 환경에서만)
    try:
        _save_ml_prediction(stock_code, record)
    except Exception as e:
        log.warning("ml_predict_db_save_failed", stock_code=stock_code, error=str(e))

    return pred.to_dict()


def _run_train(
    job_id: str,
    stock_code: str,
    horizon: int,
    config_overrides: dict[str, Any],
) -> dict[str, Any]:
    """동기 학습 코어."""
    from app.services.ml_engine import MLConfig, train_model

    ohlcv = _load_ohlcv(stock_code, lookback_days_min=400)
    if ohlcv.empty:
        raise RuntimeError(f"학습용 OHLCV 데이터 부족: {stock_code}")

    # 기본 config + override
    config_kwargs: dict[str, Any] = {
        "stock_code": stock_code,
        "horizon_days": horizon,
    }
    config_kwargs.update(config_overrides)
    config = MLConfig(**config_kwargs)

    def progress(pct: int) -> None:
        _set_train_status(
            job_id,
            {
                "job_id": job_id,
                "status": "RUNNING",
                "stock_code": stock_code,
                "horizon": horizon,
                "progress": int(pct),
            },
        )

    result = train_model(ohlcv, config, progress_cb=progress)
    return {
        "model_key": result.model_key,
        "epochs_run": result.epochs_run,
        "best_val_loss": result.best_val_loss,
        "best_val_acc": result.best_val_acc,
        "best_val_f1": result.best_val_f1,
        "model_param_count": result.model_param_count,
        "duration_sec": result.duration_sec,
        "stock_code": stock_code,
        "horizon": horizon,
    }


def _load_ohlcv(stock_code: str, lookback_days_min: int = 200):
    """동기 DB 또는 합성 OHLCV 로드.

    - ML_USE_SYNTHETIC=true 이면 합성 시계열 반환.
    - 그 외에는 동기 psycopg2 셋업이 필요하다. 본 워커는 운영 DB 동기 연결이
      없을 수 있어, 우선 합성 fallback 으로 동작하고 실제 DB 연동은 BackendDev
      가이드와 함께 후속 PR 로 보완한다.
    """
    use_synthetic = os.getenv("ML_USE_SYNTHETIC", "false").lower() == "true"
    if use_synthetic:
        from app.services.ml_engine.synthetic import make_regime_switching_series

        return make_regime_switching_series(code=stock_code, days=600)

    # DB 동기 로드 시도. SQLAlchemy 의 sync engine 으로 price_daily 조회.
    try:
        return _load_ohlcv_sync_db(stock_code)
    except Exception as e:
        log.warning("ml_db_load_failed_fallback_synthetic", stock_code=stock_code, error=str(e))
        from app.services.ml_engine.synthetic import make_regime_switching_series

        return make_regime_switching_series(code=stock_code, days=600)


def _load_ohlcv_sync_db(stock_code: str):
    """sync SQLAlchemy 로 price_daily 로드.

    `settings.DATABASE_URL` 의 asyncpg 드라이버를 psycopg2/pg8000 으로 변환해 사용한다.
    """
    import pandas as pd
    from sqlalchemy import create_engine, text

    from app.core.config import settings

    url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(url, pool_pre_ping=True)
    sql = text(
        """
        SELECT pd.trade_date, pd.open, pd.high, pd.low, pd.close, pd.volume
        FROM tp_market.price_daily pd
        JOIN tp_market.stocks s ON s.id = pd.stock_id
        WHERE s.code = :code
        ORDER BY pd.trade_date ASC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"code": stock_code}).fetchall()
    engine.dispose()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["trade_date", "open", "high", "low", "close", "volume"])
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype("int64")
    return df


def _save_ml_prediction(stock_code: str, record: dict[str, Any]) -> None:
    """ml_predictions 테이블 동기 INSERT."""
    from sqlalchemy import create_engine, text

    from app.core.config import settings

    url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        stock_id = conn.execute(
            text("SELECT id FROM tp_market.stocks WHERE code = :code"),
            {"code": stock_code},
        ).scalar_one_or_none()
        if not stock_id:
            engine.dispose()
            raise RuntimeError(f"stock not found: {stock_code}")
        conn.execute(
            text(
                """
                INSERT INTO tp_analysis.ml_predictions
                  (stock_id, base_date, horizon, pred_mean, pred_lower, pred_upper,
                   model_version, mape, direction_acc)
                VALUES
                  (:stock_id, :base_date, :horizon, :pred_mean, :pred_lower, :pred_upper,
                   :model_version, :mape, :direction_acc)
                """
            ),
            {
                "stock_id": stock_id,
                **record,
            },
        )
    engine.dispose()


def _list_active_codes() -> list[str]:
    """활성 종목 코드 리스트 (동기)."""
    from sqlalchemy import create_engine, text

    from app.core.config import settings

    url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT code FROM tp_market.stocks WHERE status = 'LISTED' ORDER BY code")
        ).fetchall()
    engine.dispose()
    return [r[0] for r in rows]


def _meta_path(stock_code: str, horizon: int) -> str:
    base = os.getenv("ML_MODEL_DIR") or _settings_model_dir()
    return os.path.join(base, f"{stock_code}_{horizon}d", "meta.json")


def _settings_model_dir() -> str:
    from app.core.config import settings

    return settings.ML_MODEL_DIR


def _model_exists(stock_code: str, horizon: int) -> bool:
    return os.path.exists(_meta_path(stock_code, horizon).replace("meta.json", "model.pt"))


def _load_config_from_meta(meta_path: str, stock_code: str, horizon: int):
    from app.services.ml_engine import MLConfig

    if not os.path.exists(meta_path):
        # 모델이 없으면 기본 설정으로 진행 (predict_from_ohlcv 가 FileNotFoundError 발생시킴)
        return MLConfig(stock_code=stock_code, horizon_days=horizon)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    return MLConfig(
        stock_code=stock_code,
        horizon_days=horizon,
        lookback_days=int(meta.get("lookback_days", 60)),
        features=list(meta.get("features", [])),
        up_threshold=float(meta.get("up_threshold", 0.01)),
        down_threshold=float(meta.get("down_threshold", -0.01)),
        hidden_size=int(meta.get("hidden_size", 64)),
        num_layers=int(meta.get("num_layers", 2)),
        dropout=float(meta.get("dropout", 0.2)),
    )


# ----------------------------------------------------------------------------
# Redis 보조 (동기)
# ----------------------------------------------------------------------------
def _store_result(prediction_id: str, payload: dict[str, Any]) -> None:
    try:
        import redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.set(f"ml:pred:result:{prediction_id}", json.dumps(payload, default=str), ex=86400)
    except Exception:
        pass


def _set_cache(key: str, payload: dict[str, Any]) -> None:
    try:
        import redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.set(key, json.dumps(payload, default=str), ex=1800)
    except Exception:
        pass


def _set_train_status(job_id: str, payload: dict[str, Any]) -> None:
    try:
        import redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.set(f"ml:train:status:{job_id}", json.dumps(payload, default=str), ex=86400)
    except Exception:
        pass


def _cache_key(code: str, horizon: int, asof: date) -> str:
    return f"ml:pred:{code}:{horizon}:{asof.isoformat()}"
