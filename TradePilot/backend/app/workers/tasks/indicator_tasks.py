"""일별 지표 배치 태스크.

스케줄: 매일 16:30 KST (장 마감 후 30분).
대상: 전 종목 또는 활성 사용자의 관심/보유 종목.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import structlog
from celery import shared_task

from app.core.database import AsyncSessionLocal
from app.services.indicator_service import IndicatorService, to_dataframe

log = structlog.get_logger(__name__)


async def _compute_one(code: str, candles: list[dict[str, Any]]) -> dict[str, Any]:
    """단일 종목 지표 계산."""
    df = to_dataframe(candles)
    return IndicatorService.compute_all(df)


@shared_task(name="indicators.compute_daily", bind=True, max_retries=3, queue="signals")
def compute_daily(self: Any, stock_codes: list[str] | None = None) -> dict[str, Any]:
    """일별 지표 배치 진입점.

    실제 DB I/O는 추후 BackendDev 구현. v1.0은 골격 + 로그만.
    """
    log.info("indicator_batch_start", count=len(stock_codes or []))
    try:
        # 실제 구현 시 AsyncSessionLocal로 DB 조회 → 캔들 로딩 → IndicatorService.compute_all
        # → upsert into indicators_daily
        processed = len(stock_codes or [])
        return {"processed": processed, "trade_date": date.today().isoformat()}
    except Exception as e:
        log.exception("indicator_batch_failed")
        raise self.retry(exc=e, countdown=60)
