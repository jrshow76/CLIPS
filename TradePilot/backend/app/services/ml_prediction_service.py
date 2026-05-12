"""ML 예측 서비스.

v1.0 동작:
- 학습은 Celery 태스크 큐잉만 (실제 모델 학습은 별도 워커에서 구현 예정)
- 예측 결과는 DB에서 조회 (없으면 mock 생성)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.analysis import MLPrediction
from app.repositories.ml_prediction_repository import MLPredictionRepository
from app.repositories.stock_repository import StockExtRepository

log = structlog.get_logger(__name__)


class MLPredictionService:
    """ML 예측 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MLPredictionRepository(db)
        self.stocks = StockExtRepository(db)

    async def get_predictions(self, code: str, *, horizon: int = 5) -> list[MLPrediction]:
        stock = await self.stocks.find_by_code(code)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")
        rows = await self.repo.list_for_stock(stock.id, limit=horizon)
        if not rows:
            # mock 생성 (실시간 추론 자리)
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

    async def enqueue_retrain(
        self, *, codes: list[str] | None, full: bool
    ) -> str:
        """학습 잡 큐잉. 반환: job_id."""
        job_id = uuid4().hex
        try:
            from app.workers.tasks.ml_tasks import retrain_lstm

            retrain_lstm.delay(job_id=job_id, codes=codes or [], full=full)
        except Exception as e:
            log.warning("ml_retrain_enqueue_failed", error=str(e))
        log.info("ml_retrain_enqueued", job_id=job_id, full=full, count=len(codes or []))
        return job_id

    # ------------------------------------------------------------------
    # 내부: mock 예측 생성
    # ------------------------------------------------------------------
    async def _mock_predictions(self, stock_id: int, *, horizon: int) -> list[MLPrediction]:
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
