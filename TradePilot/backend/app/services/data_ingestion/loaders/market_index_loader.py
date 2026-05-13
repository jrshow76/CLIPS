"""시장 지수(market_index, market_index_daily) UPSERT 로직."""
from __future__ import annotations

from typing import Iterable

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import MarketIndex, MarketIndexDaily
from app.services.data_ingestion.config import (
    INDEX_CODE_MAP,
    IngestionConfig,
    default_config,
)
from app.services.data_ingestion.sources.base import IndexBar
from app.services.data_ingestion.validator import filter_valid_index

log = structlog.get_logger(__name__)


async def upsert_market_index_master(db: AsyncSession) -> dict[str, int]:
    """지수 마스터(KOSPI/KOSDAQ/KOSPI200) 보장.

    INDEX_CODE_MAP을 기반으로 마스터 테이블 채우기.
    """
    payload = [
        {"code": code, "name": meta["name"], "market": meta["market"]}
        for code, meta in INDEX_CODE_MAP.items()
    ]
    stmt = pg_insert(MarketIndex).values(payload)
    stmt = stmt.on_conflict_do_update(
        index_elements=[MarketIndex.code],
        set_={"name": stmt.excluded.name, "market": stmt.excluded.market},
    )
    await db.execute(stmt)
    await db.commit()
    log.info("market_index_master_upserted", count=len(payload))
    return {"upserted": len(payload)}


async def upsert_market_indices(
    db: AsyncSession,
    bars: Iterable[IndexBar],
    config: IngestionConfig | None = None,
) -> dict[str, int]:
    """지수 일봉 UPSERT.

    Returns:
        {"upserted": N, "invalid": M, "missing_index": K}
    """
    cfg = config or default_config
    valid, invalid_count = filter_valid_index(bars)
    if not valid:
        return {"upserted": 0, "invalid": invalid_count, "missing_index": 0}

    # code → id 매핑
    codes = {b.code for b in valid}
    code_id_map = await _code_to_id_map(db, codes)

    payload: list[dict] = []
    missing = 0
    for b in valid:
        idx_id = code_id_map.get(b.code)
        if idx_id is None:
            missing += 1
            continue
        payload.append(
            {
                "index_id": idx_id,
                "trade_date": b.trade_date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "change_pct": b.change_pct,
            }
        )

    upserted = 0
    for chunk in _chunks(payload, cfg.chunk_size):
        if not chunk:
            continue
        stmt = pg_insert(MarketIndexDaily).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                MarketIndexDaily.index_id,
                MarketIndexDaily.trade_date,
            ],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "change_pct": stmt.excluded.change_pct,
            },
        )
        await db.execute(stmt)
        upserted += len(chunk)

    await db.commit()
    log.info(
        "market_index_daily_upserted",
        upserted=upserted,
        invalid=invalid_count,
        missing_index=missing,
    )
    return {"upserted": upserted, "invalid": invalid_count, "missing_index": missing}


async def _code_to_id_map(db: AsyncSession, codes: set[str]) -> dict[str, int]:
    if not codes:
        return {}
    stmt = select(MarketIndex.id, MarketIndex.code).where(MarketIndex.code.in_(codes))
    rows = (await db.execute(stmt)).all()
    return {row[1]: row[0] for row in rows}


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
