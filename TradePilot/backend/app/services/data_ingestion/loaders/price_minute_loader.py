"""분봉(price_minute) INSERT 로직.

- 월별 RANGE 파티셔닝 부모 테이블에 INSERT.
- 적재 전 해당 월의 파티션 보장 (자동 생성).
- (stock_id, ts, interval_min) PK 충돌 시 ON CONFLICT DO UPDATE로 멱등 처리.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import PriceMinute, Stock
from app.services.data_ingestion.config import IngestionConfig, default_config
from app.services.data_ingestion.partitioner import ensure_partition
from app.services.data_ingestion.sources.base import MinuteBar
from app.services.data_ingestion.validator import filter_valid_minute

log = structlog.get_logger(__name__)


async def insert_price_minute(
    db: AsyncSession,
    bars: Iterable[MinuteBar],
    config: IngestionConfig | None = None,
) -> dict[str, int]:
    """분봉 일괄 INSERT (UPSERT).

    Returns:
        {"inserted": N, "invalid": M, "missing_stock": K, "partitions_created": P}
    """
    cfg = config or default_config
    valid, invalid_count = filter_valid_minute(bars)
    if not valid:
        return {
            "inserted": 0,
            "invalid": invalid_count,
            "missing_stock": 0,
            "partitions_created": 0,
        }

    # 1) 적재 대상 월 파티션 보장
    months_needed: set[tuple[int, int]] = {(b.ts.year, b.ts.month) for b in valid}
    partitions_created = 0
    for year, month in sorted(months_needed):
        created = await ensure_partition(db, year, month)
        if created:
            partitions_created += 1

    # 2) code → stock_id 매핑
    codes = {b.code for b in valid}
    stock_id_map = await _code_to_id_map(db, codes)

    # 3) 페이로드 구성
    payload: list[dict] = []
    missing = 0
    for b in valid:
        sid = stock_id_map.get(b.code)
        if sid is None:
            missing += 1
            continue
        payload.append(
            {
                "stock_id": sid,
                "ts": b.ts,
                "interval_min": b.interval_min,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "volume_amount": b.volume_amount,
            }
        )

    inserted = 0
    for chunk in _chunks(payload, cfg.chunk_size):
        if not chunk:
            continue
        stmt = pg_insert(PriceMinute).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                PriceMinute.stock_id,
                PriceMinute.ts,
                PriceMinute.interval_min,
            ],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "volume_amount": stmt.excluded.volume_amount,
            },
        )
        await db.execute(stmt)
        inserted += len(chunk)

    await db.commit()
    log.info(
        "price_minute_upserted",
        inserted=inserted,
        invalid=invalid_count,
        missing_stock=missing,
        partitions_created=partitions_created,
    )
    return {
        "inserted": inserted,
        "invalid": invalid_count,
        "missing_stock": missing,
        "partitions_created": partitions_created,
    }


async def _code_to_id_map(db: AsyncSession, codes: set[str]) -> dict[str, int]:
    if not codes:
        return {}
    stmt = select(Stock.id, Stock.code).where(Stock.code.in_(codes))
    rows = (await db.execute(stmt)).all()
    return {row[1]: row[0] for row in rows}


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def group_by_month(bars: list[MinuteBar]) -> dict[tuple[int, int], list[MinuteBar]]:
    """디버깅/병렬화용: bar를 월별로 그룹핑."""
    grouped: dict[tuple[int, int], list[MinuteBar]] = defaultdict(list)
    for b in bars:
        grouped[(b.ts.year, b.ts.month)].append(b)
    return grouped
