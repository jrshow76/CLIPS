"""ML 예측 서비스.

LSTM 기반 단기 가격 방향성 예측의 유스케이스 레이어.
- 추론: 캐시(redis) 확인 → 미존재 시 Celery enqueue → prediction_id 반환
- 학습: 관리자만 호출, Celery enqueue
- 조회: DB ml_predictions 테이블 + (모델 메타 + 최근 학습 메트릭)

이전 mock 구현과의 하위 호환을 위해 기존 메서드 (`get_predictions`, `get_accuracy`,
`enqueue_retrain`) 도 유지한다.

캐시 정책: 동일 (stock_code, horizon, asof_date) 쌍은 30분 재사용
    key = "ml:pred:{code}:{horizon}:{asof_date}"
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.redis_client import get_redis
from app.models.analysis import MLPrediction
from app.repositories.ml_prediction_repository import MLPredictionRepository
from app.repositories.stock_repository import StockExtRepository

log = structlog.get_logger(__name__)

# 캐시 TTL (초)
PREDICTION_CACHE_TTL = 1800  # 30분


class MLPredictionService:
    """ML 예측 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MLPredictionRepository(db)
        self.stocks = StockExtRepository(db)

    # ==================================================================
    # 신규: 추론 요청 / 결과 조회 (분류 모델 기반)
    # ==================================================================
    async def request_prediction(
        self,
        *,
        stock_code: str,
        horizon: int,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """추론 요청.

        1) Redis 캐시 확인 (30분 내 동일 키 결과 재사용)
        2) 미존재 시 Celery enqueue + prediction_id(=task_id) 반환
        """
        if horizon not in (1, 3, 5):
            raise AppException("E0033", message="horizon 은 1/3/5 중 하나여야 합니다.")

        stock = await self.stocks.find_by_code(stock_code)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")

        cache_key = self._cache_key(stock_code, horizon, date.today())
        cached = await self._get_cache(cache_key)
        if cached:
            log.info("ml_predict_cache_hit", stock_code=stock_code, horizon=horizon)
            return {"prediction_id": cached.get("prediction_id", "cached"), "status": "DONE", "cached": True}

        prediction_id = uuid4().hex
        try:
            from app.workers.tasks.ml_tasks import predict_one  # type: ignore[attr-defined]

            predict_one.apply_async(
                kwargs={
                    "prediction_id": prediction_id,
                    "stock_code": stock_code,
                    "horizon": horizon,
                    "user_id": user_id,
                },
                task_id=prediction_id,
            )
        except Exception as e:
            log.warning("ml_predict_enqueue_failed", error=str(e))

        log.info(
            "ml_predict_enqueued",
            prediction_id=prediction_id,
            stock_code=stock_code,
            horizon=horizon,
        )
        return {"prediction_id": prediction_id, "status": "QUEUED", "cached": False}

    async def get_prediction(self, prediction_id: str) -> dict[str, Any]:
        """추론 결과 폴링.

        - Redis 캐시 우선 (Celery 결과 저장)
        - 없으면 RUNNING 또는 UNKNOWN
        """
        redis = get_redis()
        raw = await redis.get(f"ml:pred:result:{prediction_id}")
        if raw:
            return json.loads(raw)
        # Celery backend 상태 조회
        status = await self._get_celery_status(prediction_id)
        return {"prediction_id": prediction_id, "status": status}

    async def list_predictions(
        self,
        *,
        stock_code: str,
        horizon: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """종목별 최근 예측 리스트."""
        stock = await self.stocks.find_by_code(stock_code)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")
        rows = await self.repo.list_for_stock(stock.id, limit=limit)
        if horizon is not None:
            rows = [r for r in rows if r.horizon == horizon]
        return [self._row_to_dict(r, stock_code) for r in rows]

    # ==================================================================
    # 학습
    # ==================================================================
    async def request_training(
        self,
        *,
        stock_code: str,
        horizon: int = 1,
        config_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """학습 작업 큐잉. 관리자 권한 확인은 라우터에서 수행."""
        stock = await self.stocks.find_by_code(stock_code)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")
        job_id = uuid4().hex
        try:
            from app.workers.tasks.ml_tasks import train_one  # type: ignore[attr-defined]

            train_one.apply_async(
                kwargs={
                    "job_id": job_id,
                    "stock_code": stock_code,
                    "horizon": horizon,
                    "config_overrides": config_overrides or {},
                },
                task_id=job_id,
            )
        except Exception as e:
            log.warning("ml_train_enqueue_failed", error=str(e))
        log.info("ml_train_enqueued", job_id=job_id, stock_code=stock_code, horizon=horizon)
        return {"job_id": job_id, "status": "QUEUED"}

    async def get_training_status(self, job_id: str) -> dict[str, Any]:
        """학습 진행률/메트릭 조회."""
        redis = get_redis()
        raw = await redis.get(f"ml:train:status:{job_id}")
        if raw:
            return json.loads(raw)
        status = await self._get_celery_status(job_id)
        return {"job_id": job_id, "status": status}

    # ==================================================================
    # 하위 호환 (기존 라우터에서 사용)
    # ==================================================================
    async def get_predictions(self, code: str, *, horizon: int = 5) -> list[MLPrediction]:
        """기존 GET /ml-predictions/{code} 호환.

        실제 추론 결과가 DB 에 없으면 mock 행을 생성한다.
        """
        stock = await self.stocks.find_by_code(code)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")
        rows = await self.repo.list_for_stock(stock.id, limit=horizon)
        if not rows:
            rows = await self._mock_predictions(stock.id, horizon=horizon)
        return rows

    async def get_accuracy(self, code: str, *, period: str = "M") -> dict[str, Any]:
        stock = await self.stocks.find_by_code(code)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")
        latest = await self.repo.latest_accuracy(stock.id)
        if not latest:
            return {
                "code": code,
                "period": period,
                "mape": None,
                "direction_accuracy": None,
            }
        return {
            "code": code,
            "period": period,
            "mape": latest.mape,
            "direction_accuracy": latest.direction_acc,
        }

    async def enqueue_retrain(self, *, codes: list[str] | None, full: bool) -> str:
        """기존 POST /ml-predictions/retrain 호환."""
        job_id = uuid4().hex
        try:
            from app.workers.tasks.ml_tasks import retrain_lstm

            retrain_lstm.delay(job_id=job_id, codes=codes or [], full=full)
        except Exception as e:
            log.warning("ml_retrain_enqueue_failed", error=str(e))
        log.info("ml_retrain_enqueued", job_id=job_id, full=full, count=len(codes or []))
        return job_id

    # ==================================================================
    # 내부 유틸
    # ==================================================================
    @staticmethod
    def _cache_key(code: str, horizon: int, asof: date) -> str:
        return f"ml:pred:{code}:{horizon}:{asof.isoformat()}"

    @staticmethod
    async def _get_cache(key: str) -> dict[str, Any] | None:
        try:
            redis = get_redis()
            raw = await redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            return None
        return None

    @staticmethod
    async def set_cache(key: str, value: dict[str, Any]) -> None:
        try:
            redis = get_redis()
            await redis.set(key, json.dumps(value), ex=PREDICTION_CACHE_TTL)
        except Exception:
            pass

    @staticmethod
    async def _get_celery_status(task_id: str) -> str:
        """Celery AsyncResult 조회 (실패 시 UNKNOWN)."""
        try:
            from app.workers.celery_app import celery_app

            ar = celery_app.AsyncResult(task_id)
            return str(ar.status)
        except Exception:
            return "UNKNOWN"

    @staticmethod
    def _row_to_dict(row: MLPrediction, code: str) -> dict[str, Any]:
        return {
            "id": row.id,
            "code": code,
            "base_date": row.base_date.isoformat() if row.base_date else None,
            "horizon": row.horizon,
            "pred_mean": float(row.pred_mean) if row.pred_mean is not None else None,
            "pred_lower": float(row.pred_lower) if row.pred_lower is not None else None,
            "pred_upper": float(row.pred_upper) if row.pred_upper is not None else None,
            "model_version": row.model_version,
            "direction_acc": float(row.direction_acc) if row.direction_acc is not None else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def _mock_predictions(self, stock_id: int, *, horizon: int) -> list[MLPrediction]:
        """DB 데이터 없을 때 fallback. mock 행 생성."""
        latest = await self.stocks.latest_daily(stock_id)
        if not latest:
            raise AppException("E0041", message="해당 종목의 시세 데이터가 없습니다.")
        base = float(latest.close)
        today = date.today()
        rows: list[MLPrediction] = []
        for i in range(1, horizon + 1):
            mu = base * (1.0 + 0.001 * i)
            row = MLPrediction(
                stock_id=stock_id,
                base_date=today,
                horizon=i,
                pred_mean=Decimal(str(round(mu, 2))),
                pred_lower=Decimal(str(round(mu * 0.97, 2))),
                pred_upper=Decimal(str(round(mu * 1.03, 2))),
                model_version="mock-lstm-v0",
                mape=Decimal("0.05"),
                direction_acc=Decimal("0.55"),
            )
            self.db.add(row)
            rows.append(row)
        await self.db.commit()
        for r in rows:
            await self.db.refresh(r)
        return rows
