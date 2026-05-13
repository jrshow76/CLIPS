"""데이터 적재 Celery 태스크.

큐: `ingestion`

태스크 종류:
- ingest_stock_master: 매일 08:00 KST, KRX 종목 마스터/섹터 동기화
- ingest_daily_prices: 매일 16:30 KST, 전일 일봉 적재
- ingest_minute_prices: 장중 5분 간격, 활성 종목 분봉 적재
- ingest_market_indices: 매일 16:30, KOSPI/KOSDAQ/KOSPI200 일봉
- backfill_daily_prices: 관리자 트리거 백필
- ensure_minute_partitions: 매일 23:30, 다음 달 파티션 사전 생성

진행률은 Redis에 publish + result 저장.
모든 태스크는 idempotent하며, 재시도 안전.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


_PROGRESS_KEY_PREFIX = "ingest:job:"
_PROGRESS_TTL_SEC = 86400  # 24h


# ---------------------------------------------------------------------------
# 진행률 publish 헬퍼
# ---------------------------------------------------------------------------
async def _publish_progress(
    job_id: str,
    pct: int,
    status: str = "RUNNING",
    detail: dict[str, Any] | None = None,
) -> None:
    """Redis에 진행률 저장 + pub/sub 채널 publish."""
    try:
        from app.core.redis_client import get_redis

        redis = get_redis()
        payload = {
            "job_id": job_id,
            "pct": pct,
            "status": status,
            "detail": detail or {},
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        }
        body = json.dumps(payload, default=str)
        await redis.set(_PROGRESS_KEY_PREFIX + job_id, body, ex=_PROGRESS_TTL_SEC)
        await redis.publish("ingest:progress", body)
    except Exception as e:  # noqa: BLE001 - 모니터링 실패가 적재를 막지 않도록
        log.debug("progress_publish_failed", error=str(e))


def _emit_progress_sync(
    job_id: str,
    pct: int,
    status: str = "RUNNING",
    detail: dict[str, Any] | None = None,
) -> None:
    """동기 컨텍스트(태스크 본체)에서 진행률 publish."""
    try:
        asyncio.run(_publish_progress(job_id, pct, status, detail))
    except RuntimeError:
        # 이미 이벤트 루프가 도는 경우(테스트 등)
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_publish_progress(job_id, pct, status, detail))
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# 종목 마스터 + 섹터 동기화
# ---------------------------------------------------------------------------
@shared_task(
    name="ingestion.stock_master",
    queue="ingestion",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def ingest_stock_master(self: Any, job_id: str | None = None) -> dict[str, Any]:
    """KRX 종목 마스터 + 섹터 매핑 동기화."""
    job_id = job_id or self.request.id
    log.info("ingest_stock_master_start", job_id=job_id)
    try:
        result = asyncio.run(_ingest_stock_master_async(job_id))
    except Exception as e:  # noqa: BLE001
        log.exception("ingest_stock_master_failed", job_id=job_id)
        _emit_progress_sync(job_id, 0, "FAILED", {"error": str(e)[:200]})
        raise self.retry(exc=e)
    log.info("ingest_stock_master_finished", job_id=job_id, result=result)
    return result


async def _ingest_stock_master_async(job_id: str) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import (
        PyKrxSource,
        upsert_stock_sectors,
        upsert_stocks,
    )

    src = PyKrxSource()
    await _publish_progress(job_id, 5, "RUNNING", {"step": "fetch_master"})
    masters = await src.fetch_stock_master()

    await _publish_progress(job_id, 30, "RUNNING", {"step": "upsert_master"})
    async with AsyncSessionLocal() as db:
        master_stat = await upsert_stocks(db, masters)

    await _publish_progress(job_id, 60, "RUNNING", {"step": "fetch_sectors"})
    sectors = await src.fetch_sectors()

    async with AsyncSessionLocal() as db:
        sector_stat = await upsert_stock_sectors(db, sectors)

    await _publish_progress(
        job_id,
        100,
        "DONE",
        {"master": master_stat, "sectors": sector_stat},
    )
    return {"master": master_stat, "sectors": sector_stat}


# ---------------------------------------------------------------------------
# 일봉 적재
# ---------------------------------------------------------------------------
@shared_task(
    name="ingestion.daily_prices",
    queue="ingestion",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def ingest_daily_prices(
    self: Any,
    date_str: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """특정일(기본: 직전 영업일) 일봉을 적재."""
    job_id = job_id or self.request.id
    target_date = _parse_date(date_str) if date_str else _last_business_day_kst()
    log.info("ingest_daily_prices_start", job_id=job_id, date=str(target_date))
    try:
        result = asyncio.run(_ingest_daily_prices_async(target_date, job_id))
    except Exception as e:  # noqa: BLE001
        log.exception("ingest_daily_prices_failed", job_id=job_id)
        _emit_progress_sync(job_id, 0, "FAILED", {"error": str(e)[:200]})
        raise self.retry(exc=e)
    return result


async def _ingest_daily_prices_async(
    target_date: date, job_id: str
) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import backfill_daily

    async def _on_progress(pct: int, code: str | None) -> None:
        await _publish_progress(
            job_id, pct, "RUNNING", {"current_code": code, "date": str(target_date)}
        )

    async with AsyncSessionLocal() as db:
        result = await backfill_daily(
            db,
            start_date=target_date,
            end_date=target_date,
            progress_cb=_on_progress,
        )

    payload = {
        "target_codes": result.target_codes,
        "processed": result.processed_codes,
        "upserted": result.upserted_bars,
        "invalid": result.invalid_bars,
        "failed": len(result.failed_codes),
        "trade_date": str(target_date),
    }
    await _publish_progress(job_id, 100, "DONE", payload)
    return payload


# ---------------------------------------------------------------------------
# 분봉 적재
# ---------------------------------------------------------------------------
@shared_task(
    name="ingestion.minute_prices",
    queue="ingestion",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def ingest_minute_prices(
    self: Any,
    stock_codes: list[str] | None = None,
    date_str: str | None = None,
    interval_min: int = 1,
    job_id: str | None = None,
) -> dict[str, Any]:
    """장중 분봉 적재 (게이트웨이 호출).

    Args:
        stock_codes: 적재 대상 (None → 시총 상위 N종목)
        date_str: 적재 일자 (None → 오늘 KST)
        interval_min: 1/5/15/30
    """
    job_id = job_id or self.request.id
    target_date = _parse_date(date_str) if date_str else _today_kst()
    log.info(
        "ingest_minute_prices_start",
        job_id=job_id,
        date=str(target_date),
        codes=len(stock_codes or []),
    )
    try:
        result = asyncio.run(
            _ingest_minute_prices_async(stock_codes, target_date, interval_min, job_id)
        )
    except Exception as e:  # noqa: BLE001
        log.exception("ingest_minute_prices_failed", job_id=job_id)
        _emit_progress_sync(job_id, 0, "FAILED", {"error": str(e)[:200]})
        raise self.retry(exc=e)
    return result


async def _ingest_minute_prices_async(
    stock_codes: list[str] | None,
    target_date: date,
    interval_min: int,
    job_id: str,
) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import (
        CreonSource,
        default_config,
        insert_price_minute,
    )
    from app.services.data_ingestion.loaders.stock_loader import get_active_stock_codes

    cfg = default_config

    async with AsyncSessionLocal() as db:
        codes = stock_codes or await get_active_stock_codes(
            db, limit=cfg.active_codes_limit
        )

    src = CreonSource(config=cfg)
    total = len(codes)
    if total == 0:
        await _publish_progress(job_id, 100, "DONE", {"reason": "no_active_codes"})
        return {"processed": 0, "inserted": 0}

    inserted = 0
    failed: list[str] = []
    for idx, code in enumerate(codes):
        try:
            bars = await src.fetch_minute(code, target_date, interval_min)
            if bars:
                async with AsyncSessionLocal() as db:
                    stat = await insert_price_minute(db, bars, config=cfg)
                inserted += stat.get("inserted", 0)
        except Exception as e:  # noqa: BLE001
            log.warning("ingest_minute_code_failed", code=code, error=str(e)[:200])
            failed.append(code)
        if idx % 20 == 0:
            await _publish_progress(
                job_id,
                int((idx + 1) / total * 100),
                "RUNNING",
                {"current_code": code, "inserted": inserted},
            )

    payload = {
        "processed": total,
        "inserted": inserted,
        "failed": len(failed),
        "interval_min": interval_min,
        "trade_date": str(target_date),
    }
    await _publish_progress(job_id, 100, "DONE", payload)
    return payload


# ---------------------------------------------------------------------------
# 시장 지수 적재
# ---------------------------------------------------------------------------
@shared_task(
    name="ingestion.market_indices",
    queue="ingestion",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def ingest_market_indices(
    self: Any,
    date_str: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """KOSPI/KOSDAQ/KOSPI200 일봉 적재."""
    job_id = job_id or self.request.id
    target_date = _parse_date(date_str) if date_str else _last_business_day_kst()
    log.info("ingest_market_indices_start", job_id=job_id, date=str(target_date))
    try:
        result = asyncio.run(_ingest_market_indices_async(target_date, job_id))
    except Exception as e:  # noqa: BLE001
        log.exception("ingest_market_indices_failed", job_id=job_id)
        _emit_progress_sync(job_id, 0, "FAILED", {"error": str(e)[:200]})
        raise self.retry(exc=e)
    return result


async def _ingest_market_indices_async(
    target_date: date, job_id: str
) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import (
        INDEX_CODE_MAP,
        PyKrxSource,
        upsert_market_index_master,
        upsert_market_indices,
    )

    src = PyKrxSource()
    async with AsyncSessionLocal() as db:
        await upsert_market_index_master(db)

    await _publish_progress(job_id, 20, "RUNNING")

    all_bars = []
    for code in INDEX_CODE_MAP.keys():
        bars = await src.fetch_index(code, target_date, target_date)
        all_bars.extend(bars)

    async with AsyncSessionLocal() as db:
        stat = await upsert_market_indices(db, all_bars)

    payload = {**stat, "trade_date": str(target_date)}
    await _publish_progress(job_id, 100, "DONE", payload)
    return payload


# ---------------------------------------------------------------------------
# 백필
# ---------------------------------------------------------------------------
@shared_task(
    name="ingestion.backfill_daily",
    queue="ingestion",
    bind=True,
    max_retries=1,
    default_retry_delay=600,
)
def backfill_daily_prices(
    self: Any,
    start: str,
    end: str,
    codes: list[str] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """관리자가 트리거하는 일봉 백필.

    Args:
        start: YYYY-MM-DD
        end: YYYY-MM-DD
        codes: 대상 종목 (None → 전 종목)
    """
    job_id = job_id or self.request.id
    s = _parse_date(start)
    e = _parse_date(end)
    log.info(
        "backfill_daily_prices_start",
        job_id=job_id,
        start=str(s),
        end=str(e),
        codes=len(codes or []),
    )
    try:
        result = asyncio.run(_backfill_async(s, e, codes, job_id))
    except Exception as exc:  # noqa: BLE001
        log.exception("backfill_daily_prices_failed", job_id=job_id)
        _emit_progress_sync(job_id, 0, "FAILED", {"error": str(exc)[:200]})
        raise self.retry(exc=exc)
    return result


async def _backfill_async(
    start: date, end: date, codes: list[str] | None, job_id: str
) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import backfill_daily

    async def _on_progress(pct: int, code: str | None) -> None:
        await _publish_progress(job_id, pct, "RUNNING", {"current_code": code})

    async with AsyncSessionLocal() as db:
        result = await backfill_daily(
            db,
            start_date=start,
            end_date=end,
            codes=codes,
            progress_cb=_on_progress,
        )

    payload = {
        "target_codes": result.target_codes,
        "processed": result.processed_codes,
        "upserted": result.upserted_bars,
        "invalid": result.invalid_bars,
        "failed_codes": result.failed_codes[:50],  # 응답 크기 제한
        "failed_count": len(result.failed_codes),
        "start": str(start),
        "end": str(end),
    }
    await _publish_progress(job_id, 100, "DONE", payload)
    return payload


# ---------------------------------------------------------------------------
# 파티션 사전 생성
# ---------------------------------------------------------------------------
@shared_task(
    name="ingestion.ensure_minute_partitions",
    queue="ingestion",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def ensure_minute_partitions(
    self: Any,
    months: int = 2,
) -> dict[str, Any]:
    """price_minute 월별 파티션을 N개월 앞까지 보장."""
    log.info("ensure_minute_partitions_start", months=months)
    try:
        return asyncio.run(_ensure_partitions_async(months))
    except Exception as e:  # noqa: BLE001
        log.exception("ensure_minute_partitions_failed")
        raise self.retry(exc=e)


async def _ensure_partitions_async(months: int) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import ensure_partitions_lookahead

    async with AsyncSessionLocal() as db:
        created = await ensure_partitions_lookahead(db, months=months)
    return {"created_partitions": created, "count": len(created)}


# ---------------------------------------------------------------------------
# 보조 함수
# ---------------------------------------------------------------------------
def _parse_date(s: str) -> date:
    """YYYY-MM-DD 또는 YYYYMMDD."""
    s = s.strip().replace("-", "")
    return datetime.strptime(s, "%Y%m%d").date()


def _today_kst() -> date:
    from zoneinfo import ZoneInfo

    return datetime.now(tz=ZoneInfo("Asia/Seoul")).date()


def _last_business_day_kst() -> date:
    """KST 기준 직전 영업일 (주말 제외)."""
    d = _today_kst()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d
