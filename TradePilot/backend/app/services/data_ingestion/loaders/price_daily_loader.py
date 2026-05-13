"""일봉(price_daily) UPSERT 로직.

- 청크 단위로 ON CONFLICT DO UPDATE.
- (stock_id, trade_date) 복합 PK 충돌 시 최신값으로 갱신.
- 검증을 통과한 bar만 적재 (validator.filter_valid_daily 사용).
"""
from __future__ import annotations

from typing import Iterable

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import PriceDaily, Stock
from app.services.data_ingestion.config import IngestionConfig, default_config
from app.services.data_ingestion.sources.base import DailyBar
from app.services.data_ingestion.validator import filter_valid_daily

log = structlog.get_logger(__name__)


async def upsert_price_daily(
    db: AsyncSession,
    bars: Iterable[DailyBar],
    config: IngestionConfig | None = None,
) -> dict[str, int]:
    """일봉 일괄 UPSERT.

    Returns:
        {"upserted": N, "invalid": M, "missing_stock": K}
    """
    cfg = config or default_config
    valid, invalid_count = filter_valid_daily(bars)
    if not valid:
        return {"upserted": 0, "invalid": invalid_count, "missing_stock": 0}

    # 코드 → stock_id 캐시
    codes = {b.code for b in valid}
    stock_id_map = await _code_to_id_map(db, codes)

    upserted = 0
    missing = 0
    payload: list[dict] = []
    for b in valid:
        sid = stock_id_map.get(b.code)
        if sid is None:
            missing += 1
            continue
        payload.append(
            {
                "stock_id": sid,
                "trade_date": b.trade_date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "volume_amount": b.volume_amount,
                "change_pct": b.change_pct,
                "adj_close": b.adj_close,
            }
        )

    for chunk in _chunks(payload, cfg.chunk_size):
        if not chunk:
            continue
        stmt = pg_insert(PriceDaily).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[PriceDaily.stock_id, PriceDaily.trade_date],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "volume_amount": stmt.excluded.volume_amount,
                "change_pct": stmt.excluded.change_pct,
                "adj_close": stmt.excluded.adj_close,
            },
        )
        await db.execute(stmt)
        upserted += len(chunk)

    await db.commit()
    log.info(
        "price_daily_upserted",
        upserted=upserted,
        invalid=invalid_count,
        missing_stock=missing,
    )
    return {"upserted": upserted, "invalid": invalid_count, "missing_stock": missing}


async def _code_to_id_map(db: AsyncSession, codes: set[str]) -> dict[str, int]:
    if not codes:
        return {}
    stmt = select(Stock.id, Stock.code).where(Stock.code.in_(codes))
    rows = (await db.execute(stmt)).all()
    return {row[1]: row[0] for row in rows}


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]
