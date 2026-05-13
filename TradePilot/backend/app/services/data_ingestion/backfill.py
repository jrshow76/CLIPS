"""과거 데이터 백필 작업.

특징:
- 종목별로 fetch → validate → UPSERT 순환.
- 진행률 콜백(progress_cb) 지원: 0~100 정수 전달.
- 체크포인트: 실패한 종목 코드를 set으로 누적하여 재시도 가능.
- 병렬화는 외부에서 asyncio.gather 또는 별도 워커로 수행.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date
from typing import Awaitable, Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_ingestion.config import IngestionConfig, default_config
from app.services.data_ingestion.loaders.price_daily_loader import upsert_price_daily
from app.services.data_ingestion.loaders.stock_loader import get_active_stock_codes
from app.services.data_ingestion.sources.base import MarketDataSource
from app.services.data_ingestion.sources.pykrx_source import PyKrxSource

log = structlog.get_logger(__name__)


ProgressCb = Callable[[int, str | None], Awaitable[None]] | None


@dataclass(slots=True)
class BackfillResult:
    """백필 작업 결과."""

    target_codes: int = 0
    processed_codes: int = 0
    upserted_bars: int = 0
    invalid_bars: int = 0
    failed_codes: list[str] = field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None


async def backfill_daily(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    codes: list[str] | None = None,
    source: MarketDataSource | None = None,
    config: IngestionConfig | None = None,
    progress_cb: ProgressCb = None,
) -> BackfillResult:
    """일봉 과거 데이터 백필.

    Args:
        db: AsyncSession (외부 세션 재사용 권장)
        start_date: 시작일 (포함)
        end_date: 종료일 (포함)
        codes: 대상 종목 코드 (None → 모든 LISTED 종목)
        source: 데이터 소스 (None → PyKrxSource 기본)
        config: 적재 설정
        progress_cb: 진행률 콜백 (pct, current_code)

    Returns:
        BackfillResult
    """
    from datetime import datetime, timezone

    cfg = config or default_config
    src = source or PyKrxSource(config=cfg)

    if codes is None:
        codes = await get_active_stock_codes(db)
    target_codes = list(dict.fromkeys(codes))  # 중복 제거 + 순서 유지

    result = BackfillResult(
        target_codes=len(target_codes),
        started_at=datetime.now(tz=timezone.utc).isoformat(),
    )

    log.info(
        "backfill_started",
        codes=len(target_codes),
        start=str(start_date),
        end=str(end_date),
    )

    for idx, code in enumerate(target_codes):
        try:
            bars = await src.fetch_daily(code, start_date, end_date)
            stat = await upsert_price_daily(db, bars, config=cfg)
            result.upserted_bars += stat.get("upserted", 0)
            result.invalid_bars += stat.get("invalid", 0)
        except Exception as e:  # noqa: BLE001
            log.warning("backfill_code_failed", code=code, error=str(e)[:200])
            result.failed_codes.append(code)
        finally:
            result.processed_codes += 1

        if progress_cb is not None:
            pct = int((idx + 1) / max(len(target_codes), 1) * 100)
            try:
                await progress_cb(pct, code)
            except Exception:  # noqa: BLE001
                pass

        # 부드러운 throttle: 각 종목 사이 짧은 sleep
        await asyncio.sleep(0)

    result.finished_at = datetime.now(tz=timezone.utc).isoformat()
    log.info(
        "backfill_finished",
        processed=result.processed_codes,
        upserted=result.upserted_bars,
        failed=len(result.failed_codes),
    )
    return result


async def retry_failed(
    db: AsyncSession,
    failed_codes: list[str],
    start_date: date,
    end_date: date,
    source: MarketDataSource | None = None,
    config: IngestionConfig | None = None,
) -> BackfillResult:
    """실패 종목 재시도 (체크포인트 복원)."""
    return await backfill_daily(
        db,
        start_date=start_date,
        end_date=end_date,
        codes=failed_codes,
        source=source,
        config=config,
    )
