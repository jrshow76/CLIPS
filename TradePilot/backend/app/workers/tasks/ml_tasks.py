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
def batch_predict(
    self,
    horizons: list[int] | None = None,
    ensemble: bool = True,
) -> dict[str, Any]:
    """모든 활성 종목 일괄 추론.

    Args:
        horizons: 추론 호라이즌 리스트
        ensemble: True 이면 앙상블(개별/섹터/글로벌 가중 평균), False 면 기존 단일.
                  앙상블 시 어떤 모델이라도 존재하면 처리한다.
    """
    horizons = horizons or [1]
    results: dict[str, Any] = {
        "horizons": horizons,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "ensemble": ensemble,
    }

    try:
        codes = _list_active_codes()
    except Exception as e:
        log.warning("ml_batch_predict_load_codes_failed", error=str(e))
        return {**results, "status": "FAILED", "error": str(e)}

    log.info("ml_batch_predict_started", n_codes=len(codes), horizons=horizons, ensemble=ensemble)
    for code in codes:
        for h in horizons:
            if ensemble:
                # 앙상블: 한 종류라도 모델이 있으면 시도
                if not _any_model_exists(code, h):
                    results["skipped"] += 1
                    continue
                try:
                    _run_ensemble_predict(stock_code=code, horizon=h)
                    results["processed"] += 1
                except Exception as e:
                    log.warning(
                        "ml_batch_predict_ensemble_failed",
                        code=code, horizon=h, error=str(e),
                    )
                    results["failed"] += 1
            else:
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


def _any_model_exists(stock_code: str, horizon: int) -> bool:
    """앙상블 가능한 모델이 하나라도 있는지."""
    from app.services.ml_engine import (
        global_model_exists,
        model_exists,
        sector_model_exists,
    )

    if model_exists(stock_code, horizon):
        return True
    if global_model_exists(horizon):
        return True
    # 섹터 모델은 stock 의 sector 가 필요 (없으면 false)
    sector_code = _get_stock_sector(stock_code)
    if sector_code and sector_model_exists(sector_code, horizon):
        return True
    return False


def _run_ensemble_predict(stock_code: str, horizon: int) -> dict[str, Any]:
    """앙상블 추론 코어."""
    from app.services.ml_engine import predict_ensemble, predictions_to_ml_record

    ohlcv = _load_ohlcv(stock_code, lookback_days_min=200)
    if ohlcv.empty:
        raise RuntimeError(f"OHLCV 데이터 없음: {stock_code}")

    sector_code = _get_stock_sector(stock_code)
    ensemble_result = predict_ensemble(
        ohlcv=ohlcv,
        stock_code=stock_code,
        horizon=horizon,
        sector_code=sector_code,
    )

    # PredictionResult 호환 형태로 변환 (DB 저장용)
    from app.services.ml_engine import PredictionResult

    pseudo = PredictionResult(
        direction=ensemble_result.direction,
        confidence=ensemble_result.confidence,
        prob_down=ensemble_result.prob_down,
        prob_flat=ensemble_result.prob_flat,
        prob_up=ensemble_result.prob_up,
        model_key=f"ensemble-{horizon}d",
        asof_date=ensemble_result.asof_date,
        horizon_days=horizon,
    )
    record = predictions_to_ml_record(pseudo, last_close=float(ohlcv["close"].iloc[-1]))

    try:
        _save_ml_prediction(stock_code, record)
    except Exception as e:
        log.warning("ml_ensemble_predict_db_save_failed", stock_code=stock_code, error=str(e))

    return ensemble_result.to_dict()


def _get_stock_sector(stock_code: str) -> str | None:
    """종목의 섹터 코드 조회 (실패 시 None)."""
    try:
        from sqlalchemy import create_engine, text

        from app.core.config import settings

        url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine = create_engine(url, pool_pre_ping=True)
        sql = text(
            """
            SELECT sec.code FROM tp_market.stocks s
            JOIN tp_market.sectors sec ON sec.id = s.sector_id
            WHERE s.code = :code
            """
        )
        with engine.connect() as conn:
            row = conn.execute(sql, {"code": stock_code}).fetchone()
        engine.dispose()
        return str(row[0]) if row else None
    except Exception:
        return None


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
# 학습 락 (CPU 자원 보호: 동시 1개)
# ============================================================================
_TRAIN_LOCK_KEY = "ml:train:lock"
_TRAIN_LOCK_TTL = 7200  # 2시간


def _acquire_train_lock(holder: str) -> bool:
    """학습 동시성 락 획득 (Redis SETNX). Redis 미가용 시 True."""
    try:
        import redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return bool(r.set(_TRAIN_LOCK_KEY, holder, nx=True, ex=_TRAIN_LOCK_TTL))
    except Exception:
        return True


def _release_train_lock(holder: str) -> None:
    """학습 락 해제 (자신이 보유한 경우만)."""
    try:
        import redis

        from app.core.config import settings

        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        cur = r.get(_TRAIN_LOCK_KEY)
        if cur == holder:
            r.delete(_TRAIN_LOCK_KEY)
    except Exception:
        pass


# ============================================================================
# 섹터 모델 학습
# ============================================================================
@shared_task(
    name="ml.train_sector",
    queue="ml",
    bind=True,
    max_retries=1,
    time_limit=7200,
)
def train_sector(
    self,
    job_id: str,
    sector_code: str,
    stock_codes: list[str],
    horizon: int = 1,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """섹터 모델 학습."""
    started = datetime.now(UTC)
    if not _acquire_train_lock(job_id):
        return {
            "job_id": job_id,
            "status": "SKIPPED",
            "reason": "다른 학습 작업이 진행 중",
            "sector_code": sector_code,
        }

    _set_train_status(job_id, {
        "job_id": job_id,
        "status": "RUNNING",
        "kind": "SECTOR",
        "sector_code": sector_code,
        "horizon": horizon,
        "n_stocks": len(stock_codes),
        "progress": 0,
        "started_at": started.isoformat(),
    })
    log.info(
        "ml_train_sector_started",
        job_id=job_id,
        sector_code=sector_code,
        n_stocks=len(stock_codes),
        horizon=horizon,
    )
    try:
        result = _run_train_sector(
            job_id=job_id,
            sector_code=sector_code,
            stock_codes=stock_codes,
            horizon=horizon,
            config_overrides=config_overrides or {},
        )
        result.update({
            "job_id": job_id,
            "status": "DONE",
            "kind": "SECTOR",
            "sector_code": sector_code,
            "started_at": started.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
        })
        _set_train_status(job_id, result)
        log.info("ml_train_sector_done", job_id=job_id, **{
            k: result.get(k) for k in ("best_val_acc", "duration_sec", "n_stocks")
        })
        return result
    except Exception as e:  # pragma: no cover
        log.warning("ml_train_sector_failed", job_id=job_id, error=str(e))
        failure = {
            "job_id": job_id,
            "status": "FAILED",
            "kind": "SECTOR",
            "sector_code": sector_code,
            "horizon": horizon,
            "error": str(e),
        }
        _set_train_status(job_id, failure)
        return failure
    finally:
        _release_train_lock(job_id)


# ============================================================================
# 글로벌 모델 학습
# ============================================================================
@shared_task(
    name="ml.train_global",
    queue="ml",
    bind=True,
    max_retries=1,
    time_limit=10800,  # 3시간 (전 종목)
)
def train_global(
    self,
    job_id: str,
    stock_codes: list[str] | None = None,
    horizon: int = 1,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """글로벌 모델 학습 (종목 임베딩 포함)."""
    started = datetime.now(UTC)
    if not _acquire_train_lock(job_id):
        return {
            "job_id": job_id,
            "status": "SKIPPED",
            "reason": "다른 학습 작업이 진행 중",
        }

    codes = stock_codes or _safe_list_active_codes()
    _set_train_status(job_id, {
        "job_id": job_id,
        "status": "RUNNING",
        "kind": "GLOBAL",
        "horizon": horizon,
        "n_stocks": len(codes),
        "progress": 0,
        "started_at": started.isoformat(),
    })
    log.info("ml_train_global_started", job_id=job_id, n_stocks=len(codes), horizon=horizon)
    try:
        result = _run_train_multistock(
            job_id=job_id,
            stock_codes=codes,
            horizon=horizon,
            config_overrides=config_overrides or {},
        )
        result.update({
            "job_id": job_id,
            "status": "DONE",
            "kind": "GLOBAL",
            "started_at": started.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
        })
        _set_train_status(job_id, result)
        log.info(
            "ml_train_global_done",
            job_id=job_id,
            best_val_acc=result.get("best_val_acc"),
            duration_sec=result.get("duration_sec"),
            n_stocks=result.get("n_stocks"),
        )
        return result
    except Exception as e:  # pragma: no cover
        log.warning("ml_train_global_failed", job_id=job_id, error=str(e))
        failure = {
            "job_id": job_id,
            "status": "FAILED",
            "kind": "GLOBAL",
            "horizon": horizon,
            "error": str(e),
        }
        _set_train_status(job_id, failure)
        return failure
    finally:
        _release_train_lock(job_id)


# ============================================================================
# 전 섹터 일괄 학습 (스케줄러용)
# ============================================================================
@shared_task(
    name="ml.train_all_sectors",
    queue="ml",
    bind=True,
    time_limit=21600,  # 6시간
)
def train_all_sectors(
    self,
    horizon: int = 1,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """모든 섹터를 순차적으로 학습 (CPU 보호용 직렬 실행)."""
    sectors = _safe_list_sectors_with_stocks()
    if not sectors:
        log.info("ml_train_all_sectors_no_sectors")
        return {"status": "DONE", "n_sectors": 0}

    results: list[dict[str, Any]] = []
    log.info("ml_train_all_sectors_started", n_sectors=len(sectors), horizon=horizon)
    for sector_code, codes in sectors:
        job_id = f"sector-{sector_code}-{horizon}-{int(datetime.now(UTC).timestamp())}"
        try:
            res = train_sector(  # 직접 호출 (apply_async 가 아닌 순차 직렬)
                job_id=job_id,
                sector_code=sector_code,
                stock_codes=codes,
                horizon=horizon,
                config_overrides=config_overrides or {},
            )
            results.append({"sector": sector_code, "status": res.get("status"), "job_id": job_id})
        except Exception as e:
            log.warning(
                "ml_train_all_sectors_per_sector_failed",
                sector_code=sector_code,
                error=str(e),
            )
            results.append({"sector": sector_code, "status": "FAILED", "error": str(e)})

    log.info("ml_train_all_sectors_done", n_sectors=len(results))
    return {"status": "DONE", "horizon": horizon, "results": results}


# ============================================================================
# 멀티 모델 학습 코어 헬퍼
# ============================================================================
def _run_train_sector(
    *,
    job_id: str,
    sector_code: str,
    stock_codes: list[str],
    horizon: int,
    config_overrides: dict[str, Any],
) -> dict[str, Any]:
    """섹터 학습 동기 코어."""
    from app.services.ml_engine import MLConfig, train_sector_model

    ohlcv_map: dict[str, Any] = {}
    for code in stock_codes:
        df = _load_ohlcv(code, lookback_days_min=400)
        if df is not None and not df.empty:
            ohlcv_map[code] = df

    if not ohlcv_map:
        raise RuntimeError(f"섹터 {sector_code} 학습용 OHLCV 데이터가 없습니다")

    config_kwargs: dict[str, Any] = {
        "stock_code": sector_code,  # 식별자 용도 (실제 학습에서는 미사용)
        "horizon_days": horizon,
    }
    config_kwargs.update(config_overrides)
    config = MLConfig(**config_kwargs)

    def progress(pct: int) -> None:
        _set_train_status(job_id, {
            "job_id": job_id,
            "status": "RUNNING",
            "kind": "SECTOR",
            "sector_code": sector_code,
            "horizon": horizon,
            "progress": int(pct),
            "n_stocks": len(ohlcv_map),
        })

    result = train_sector_model(
        sector_code=sector_code,
        ohlcv_by_code=ohlcv_map,
        config=config,
        progress_cb=progress,
    )
    return {
        "model_key": result.model_key,
        "model_kind": result.model_kind,
        "n_stocks": result.n_stocks,
        "epochs_run": result.epochs_run,
        "best_val_loss": result.best_val_loss,
        "best_val_acc": result.best_val_acc,
        "best_val_f1": result.best_val_f1,
        "per_stock_val_acc": result.per_stock_val_acc,
        "duration_sec": result.duration_sec,
        "model_param_count": result.model_param_count,
        "horizon": horizon,
    }


def _run_train_multistock(
    *,
    job_id: str,
    stock_codes: list[str],
    horizon: int,
    config_overrides: dict[str, Any],
) -> dict[str, Any]:
    """글로벌 학습 동기 코어."""
    from app.services.ml_engine import MLConfig, train_multistock_model

    ohlcv_map: dict[str, Any] = {}
    for code in stock_codes:
        df = _load_ohlcv(code, lookback_days_min=400)
        if df is not None and not df.empty:
            ohlcv_map[code] = df

    if not ohlcv_map:
        raise RuntimeError("글로벌 학습용 OHLCV 데이터가 없습니다")

    config_kwargs: dict[str, Any] = {
        "stock_code": "global",
        "horizon_days": horizon,
    }
    config_kwargs.update(config_overrides)
    config = MLConfig(**config_kwargs)

    def progress(pct: int) -> None:
        _set_train_status(job_id, {
            "job_id": job_id,
            "status": "RUNNING",
            "kind": "GLOBAL",
            "horizon": horizon,
            "progress": int(pct),
            "n_stocks": len(ohlcv_map),
        })

    result = train_multistock_model(
        ohlcv_by_code=ohlcv_map,
        config=config,
        progress_cb=progress,
    )
    return {
        "model_key": result.model_key,
        "model_kind": result.model_kind,
        "n_stocks": result.n_stocks,
        "epochs_run": result.epochs_run,
        "best_val_loss": result.best_val_loss,
        "best_val_acc": result.best_val_acc,
        "best_val_f1": result.best_val_f1,
        "per_stock_val_acc": result.per_stock_val_acc,
        "duration_sec": result.duration_sec,
        "model_param_count": result.model_param_count,
        "horizon": horizon,
    }


def _safe_list_active_codes() -> list[str]:
    try:
        return _list_active_codes()
    except Exception as e:
        log.warning("ml_list_active_codes_failed", error=str(e))
        # 합성 fallback (개발/CI 환경)
        if os.getenv("ML_USE_SYNTHETIC", "false").lower() == "true":
            return [f"SYN{i:03d}" for i in range(10)]
        return []


def _safe_list_sectors_with_stocks() -> list[tuple[str, list[str]]]:
    """섹터별 종목 리스트 (안전 fallback 포함)."""
    try:
        return _list_sectors_with_stocks()
    except Exception as e:
        log.warning("ml_list_sectors_failed", error=str(e))
        if os.getenv("ML_USE_SYNTHETIC", "false").lower() == "true":
            return [
                ("SEMI", [f"SEMI{i:03d}" for i in range(5)]),
                ("FIN", [f"FIN{i:03d}" for i in range(5)]),
                ("BIO", [f"BIO{i:03d}" for i in range(5)]),
            ]
        return []


def _list_sectors_with_stocks() -> list[tuple[str, list[str]]]:
    """tp_market.sectors / stocks 조인으로 섹터별 종목 리스트."""
    from sqlalchemy import create_engine, text

    from app.core.config import settings

    url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(url, pool_pre_ping=True)
    sql = text(
        """
        SELECT sec.code AS sector_code, s.code AS stock_code
        FROM tp_market.stocks s
        JOIN tp_market.sectors sec ON sec.id = s.sector_id
        WHERE s.status = 'LISTED'
        ORDER BY sec.code, s.code
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    engine.dispose()

    grouped: dict[str, list[str]] = {}
    for sector_code, stock_code in rows:
        grouped.setdefault(str(sector_code), []).append(str(stock_code))
    return list(grouped.items())


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
