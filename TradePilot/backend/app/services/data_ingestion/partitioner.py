"""price_minute 파티션 동적 생성.

`tp_market.price_minute`는 RANGE(ts) 파티셔닝 부모 테이블이다.
월 단위 자식 파티션을 자동 생성하여 분봉 적재가 실패하지 않도록 한다.

파티션 명명 규칙:
    tp_market.price_minute_yYYYYmMM
예:
    tp_market.price_minute_y2026m05
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


def _partition_name(year: int, month: int) -> str:
    return f"price_minute_y{year:04d}m{month:02d}"


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """[start, end) 경계 반환 (end는 다음 달 1일)."""
    last_day = monthrange(year, month)[1]
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    _ = last_day  # 명시
    return start, end


def build_partition_ddl(year: int, month: int, schema: str = "tp_market") -> str:
    """파티션 생성 DDL 문자열 생성 (테스트 가능하도록 분리)."""
    name = _partition_name(year, month)
    start, end = _month_bounds(year, month)
    # `IF NOT EXISTS`는 PG13+ 부터 PARTITION OF 에 지원
    return (
        f"CREATE TABLE IF NOT EXISTS {schema}.{name} "
        f"PARTITION OF {schema}.price_minute "
        f"FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}');"
    )


def build_partition_index_ddl(
    year: int, month: int, schema: str = "tp_market"
) -> list[str]:
    """파티션별 보조 인덱스 DDL.

    조회 패턴: stock_id + ts 범위 → (stock_id, ts) 인덱스
    """
    name = _partition_name(year, month)
    return [
        (
            f"CREATE INDEX IF NOT EXISTS ix_{name}_stock_ts "
            f"ON {schema}.{name} (stock_id, ts);"
        ),
    ]


async def ensure_partition(
    db: AsyncSession,
    year: int,
    month: int,
    schema: str = "tp_market",
) -> bool:
    """월별 파티션을 보장한다 (없으면 생성).

    Returns:
        True - 새로 생성됨, False - 이미 존재
    """
    name = _partition_name(year, month)
    # 존재 여부 확인
    check_sql = text(
        "SELECT 1 FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = :schema AND c.relname = :name LIMIT 1"
    )
    exists = (
        await db.execute(check_sql, {"schema": schema, "name": name})
    ).scalar_one_or_none()
    if exists:
        return False

    ddl = build_partition_ddl(year, month, schema)
    log.info("creating_partition", name=name, ddl=ddl)
    await db.execute(text(ddl))
    for idx_ddl in build_partition_index_ddl(year, month, schema):
        await db.execute(text(idx_ddl))
    await db.commit()
    return True


async def ensure_partitions_for_range(
    db: AsyncSession,
    start: date,
    end: date,
    schema: str = "tp_market",
) -> list[str]:
    """[start, end] 범위에 걸친 월별 파티션 모두 보장.

    Returns:
        새로 생성된 파티션명 목록
    """
    created: list[str] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        ok = await ensure_partition(db, y, m, schema)
        if ok:
            created.append(_partition_name(y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return created


async def ensure_partitions_lookahead(
    db: AsyncSession,
    months: int = 2,
    reference: date | None = None,
    schema: str = "tp_market",
) -> list[str]:
    """현재 시점부터 N개월 앞까지 파티션 사전 생성.

    스케줄러가 매일 한 번 호출하면 안전하다.
    """
    ref = reference or date.today()
    end = ref
    for _ in range(months):
        if end.month == 12:
            end = date(end.year + 1, 1, 1)
        else:
            end = date(end.year, end.month + 1, 1)
    return await ensure_partitions_for_range(db, ref, end, schema)
