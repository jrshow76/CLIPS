"""종목 마스터 / 섹터 / 종목-섹터 매핑 UPSERT 로직."""
from __future__ import annotations

from typing import Iterable

import structlog
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Sector, Stock, StockSector
from app.services.data_ingestion.config import IngestionConfig, default_config
from app.services.data_ingestion.sources.base import StockMasterRow, StockSectorRow

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# 종목 마스터 UPSERT
# ---------------------------------------------------------------------------
async def upsert_stocks(
    db: AsyncSession,
    rows: Iterable[StockMasterRow],
    config: IngestionConfig | None = None,
) -> dict[str, int]:
    """종목 마스터 일괄 UPSERT.

    동작:
    - code 기준 ON CONFLICT DO UPDATE
    - 결과 통계 반환 (inserted/updated 합산은 PG가 구분 불가 → upserted만)
    - 섹터 매핑 시 stock_id 조회를 위해 캐시도 반환 가능 (외부에서 별도 조회)

    Returns:
        {"upserted": N}
    """
    cfg = config or default_config
    rows_list = list(rows)
    if not rows_list:
        return {"upserted": 0}

    upserted_total = 0
    for chunk in _chunks(rows_list, cfg.chunk_size):
        payload = [
            {
                "code": r.code,
                "name": r.name,
                "market": r.market,
                "status": r.status,
                "listing_shares": r.listing_shares,
                "market_cap": r.market_cap,
                "par_value": r.par_value,
                "listed_at": r.listed_at,
            }
            for r in chunk
        ]
        stmt = pg_insert(Stock).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Stock.code],
            set_={
                "name": stmt.excluded.name,
                "market": stmt.excluded.market,
                "status": stmt.excluded.status,
                "listing_shares": stmt.excluded.listing_shares,
                "market_cap": stmt.excluded.market_cap,
                "par_value": stmt.excluded.par_value,
                "listed_at": stmt.excluded.listed_at,
            },
        )
        await db.execute(stmt)
        upserted_total += len(payload)

    await db.commit()
    log.info("stocks_upserted", count=upserted_total)
    return {"upserted": upserted_total}


# ---------------------------------------------------------------------------
# 섹터 + 종목-섹터 매핑 UPSERT
# ---------------------------------------------------------------------------
async def upsert_stock_sectors(
    db: AsyncSession,
    mappings: Iterable[StockSectorRow],
    config: IngestionConfig | None = None,
) -> dict[str, int]:
    """섹터 마스터 + 종목-섹터 매핑 UPSERT.

    섹터를 먼저 보장한 뒤 stock_id/sector_id를 조회하여 매핑을 INSERT한다.
    중복 매핑은 ON CONFLICT DO NOTHING.
    """
    cfg = config or default_config
    mappings_list = list(mappings)
    if not mappings_list:
        return {"sectors": 0, "mappings": 0}

    # 1) 섹터 UPSERT
    unique_sectors = {(m.sector_code, m.sector_name) for m in mappings_list}
    sector_payload = [
        {"code": code, "name": name, "sort_order": 0}
        for code, name in sorted(unique_sectors)
    ]
    if sector_payload:
        for chunk in _chunks(sector_payload, cfg.chunk_size):
            stmt = pg_insert(Sector).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Sector.code],
                set_={"name": stmt.excluded.name},
            )
            await db.execute(stmt)
        await db.commit()

    # 2) ID 조회
    stock_codes = {m.stock_code for m in mappings_list}
    sector_codes = {m.sector_code for m in mappings_list}

    stock_id_map = await _resolve_ids(db, Stock, "code", stock_codes)
    sector_id_map = await _resolve_ids(db, Sector, "code", sector_codes)

    # 3) 매핑 INSERT
    mapping_payload = []
    for m in mappings_list:
        sid = stock_id_map.get(m.stock_code)
        secid = sector_id_map.get(m.sector_code)
        if sid is None or secid is None:
            continue
        mapping_payload.append(
            {"stock_id": sid, "sector_id": secid, "is_primary": m.is_primary}
        )

    inserted = 0
    for chunk in _chunks(mapping_payload, cfg.chunk_size):
        if not chunk:
            continue
        stmt = pg_insert(StockSector).values(chunk)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=[StockSector.stock_id, StockSector.sector_id]
        )
        await db.execute(stmt)
        inserted += len(chunk)

    await db.commit()
    log.info(
        "stock_sectors_upserted",
        sectors=len(sector_payload),
        mappings=inserted,
    )
    return {"sectors": len(sector_payload), "mappings": inserted}


# ---------------------------------------------------------------------------
# 보조 함수
# ---------------------------------------------------------------------------
async def _resolve_ids(
    db: AsyncSession,
    model_cls: type,
    code_col: str,
    codes: set[str],
) -> dict[str, int]:
    """code → id 매핑 조회."""
    if not codes:
        return {}
    col = getattr(model_cls, code_col)
    stmt = select(model_cls.id, col).where(col.in_(codes))
    rows = (await db.execute(stmt)).all()
    return {row[1]: row[0] for row in rows}


def _chunks(items: list, size: int):
    """리스트를 size 단위로 분할."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def get_active_stock_codes(
    db: AsyncSession, limit: int | None = None
) -> list[str]:
    """활성(LISTED) 종목 코드 조회.

    장중 분봉 적재 시 대상 종목 선정에 사용.
    """
    stmt = (
        select(Stock.code)
        .where(Stock.status == "LISTED")
        .order_by(Stock.market_cap.desc().nulls_last(), Stock.code.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).all()
    return [r[0] for r in rows]
