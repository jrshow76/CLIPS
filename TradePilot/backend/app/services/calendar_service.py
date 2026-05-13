"""시장 캘린더 서비스.

KRX 등 시장 휴장일을 단일 소스(`tp_market.market_calendar`)로 관리한다.

특징
----
1. **단일 소스**: market_service / backtest / ingestion / scheduler 전부
   본 서비스를 통해 휴장일을 조회한다. 하드코딩된 KR_HOLIDAYS 는 제거.
2. **캐시**: 연도별 휴장일 집합을 Redis 30분 캐시로 보관.
   휴장일 추가/삭제/동기화 시 캐시는 invalidate.
3. **pykrx 동기화**: `sync_from_krx(year)`. pykrx 미설치 환경에서는
   ImportError 시 시드 데이터를 그대로 유지하고 빈 결과를 리턴 (안전 fallback).
4. **타임존**: 모든 날짜 비교는 한국 시간(Asia/Seoul) 기준.

REGULAR(법정/정기)만 자동 동기화 대상이며, TEMPORARY(임시휴장)는
운영자가 `add_holiday(..., source='manual')` 로 명시 등록한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.redis_client import (
    cache_delete,
    cache_get_json,
    cache_set_json,
    get_redis,
)
from app.models.market import MarketCalendar

log = structlog.get_logger(__name__)

KST = ZoneInfo("Asia/Seoul")

# 캐시 키/TTL
_CACHE_TTL_SEC = 30 * 60  # 30분
_CACHE_PREFIX = "market:calendar"

# 허용 type / source 값
_ALLOWED_TYPES = {"REGULAR", "TEMPORARY", "SUBSTITUTE"}
_ALLOWED_SOURCES = {"pykrx", "manual", "seed"}


@dataclass(frozen=True)
class Holiday:
    """휴장일 DTO."""

    date: date
    name: str
    type: str
    market: str = "KRX"
    source: str = "pykrx"
    description: str | None = None


def _cache_key(market: str, year: int) -> str:
    return f"{_CACHE_PREFIX}:{market}:{year}"


class CalendarService:
    """시장 캘린더 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 조회
    # ------------------------------------------------------------------
    async def get_holidays(self, year: int, market: str = "KRX") -> list[Holiday]:
        """연도별 휴장일 목록 (캐시 적용)."""
        key = _cache_key(market, year)
        cached = await cache_get_json(key)
        if cached is not None:
            return [
                Holiday(
                    date=date.fromisoformat(h["date"]),
                    name=h["name"],
                    type=h["type"],
                    market=h.get("market", market),
                    source=h.get("source", "pykrx"),
                    description=h.get("description"),
                )
                for h in cached
            ]

        start = date(year, 1, 1)
        end = date(year, 12, 31)
        stmt = (
            select(MarketCalendar)
            .where(
                MarketCalendar.market == market,
                MarketCalendar.holiday_date >= start,
                MarketCalendar.holiday_date <= end,
            )
            .order_by(MarketCalendar.holiday_date.asc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        holidays = [
            Holiday(
                date=r.holiday_date,
                name=r.holiday_name,
                type=r.holiday_type,
                market=r.market,
                source=r.source,
                description=r.description,
            )
            for r in rows
        ]

        # 캐시 적재 (30분)
        await cache_set_json(
            key,
            [
                {
                    "date": h.date.isoformat(),
                    "name": h.name,
                    "type": h.type,
                    "market": h.market,
                    "source": h.source,
                    "description": h.description,
                }
                for h in holidays
            ],
            _CACHE_TTL_SEC,
        )
        return holidays

    async def is_holiday(self, target: date, market: str = "KRX") -> bool:
        """휴장일 여부 (DB 조회 + 캐시).

        주말은 본 메서드에서는 처리하지 않는다 (`is_business_day` 참조).
        """
        holidays = await self.get_holidays(target.year, market)
        return any(h.date == target for h in holidays)

    async def is_business_day(self, target: date, market: str = "KRX") -> bool:
        """영업일 여부 = 평일이면서 휴장일이 아닌 날."""
        if target.weekday() >= 5:  # 토(5)/일(6)
            return False
        return not await self.is_holiday(target, market)

    async def next_business_day(self, target: date, market: str = "KRX") -> date:
        """target 이후 가장 가까운 영업일 (target 미포함).

        최대 60일 탐색. 60일 내 영업일이 없으면 예외 (E0061).
        """
        candidate = target + timedelta(days=1)
        for _ in range(60):
            if await self.is_business_day(candidate, market):
                return candidate
            candidate = candidate + timedelta(days=1)
        raise AppException("E0061", message="다음 영업일을 찾을 수 없습니다.")

    async def previous_business_day(self, target: date, market: str = "KRX") -> date:
        """target 이전 가장 가까운 영업일 (target 미포함)."""
        candidate = target - timedelta(days=1)
        for _ in range(60):
            if await self.is_business_day(candidate, market):
                return candidate
            candidate = candidate - timedelta(days=1)
        raise AppException("E0061", message="이전 영업일을 찾을 수 없습니다.")

    async def business_days_between(
        self, start: date, end: date, market: str = "KRX"
    ) -> int:
        """[start, end] 구간(양 끝 포함) 영업일 수."""
        if end < start:
            return 0
        cnt = 0
        cur = start
        # 너무 큰 구간 방지 (5년)
        if (end - start).days > 365 * 5:
            raise AppException("E0063", message="요청 기간이 너무 깁니다.")
        while cur <= end:
            if await self.is_business_day(cur, market):
                cnt += 1
            cur = cur + timedelta(days=1)
        return cnt

    # ------------------------------------------------------------------
    # 변경 (관리자)
    # ------------------------------------------------------------------
    async def add_holiday(
        self,
        target: date,
        name: str,
        holiday_type: str = "TEMPORARY",
        *,
        market: str = "KRX",
        source: str = "manual",
        description: str | None = None,
    ) -> Holiday:
        """휴장일 등록 (UPSERT). 이미 존재하면 이름/타입/설명만 갱신."""
        if holiday_type not in _ALLOWED_TYPES:
            raise AppException(
                "E0003",
                message="holiday_type 이 올바르지 않습니다.",
                details={"allowed": sorted(_ALLOWED_TYPES), "given": holiday_type},
            )
        if source not in _ALLOWED_SOURCES:
            raise AppException(
                "E0003",
                message="source 가 올바르지 않습니다.",
                details={"allowed": sorted(_ALLOWED_SOURCES), "given": source},
            )

        stmt = pg_insert(MarketCalendar).values(
            holiday_date=target,
            holiday_name=name,
            holiday_type=holiday_type,
            market=market,
            source=source,
            description=description,
        )
        # (market, holiday_date) UNIQUE 기준 UPSERT
        stmt = stmt.on_conflict_do_update(
            index_elements=["market", "holiday_date"],
            set_={
                "holiday_name": stmt.excluded.holiday_name,
                "holiday_type": stmt.excluded.holiday_type,
                "source": stmt.excluded.source,
                "description": stmt.excluded.description,
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()

        # 캐시 무효화
        await cache_delete(_cache_key(market, target.year))

        log.info(
            "calendar_holiday_added",
            date=target.isoformat(),
            name=name,
            type=holiday_type,
            source=source,
            market=market,
        )
        return Holiday(
            date=target,
            name=name,
            type=holiday_type,
            market=market,
            source=source,
            description=description,
        )

    async def remove_holiday(
        self,
        target: date,
        market: str = "KRX",
        *,
        actor_user_id: int | None = None,
    ) -> bool:
        """휴장일 삭제. 감사 로그(structlog) 기록.

        Returns:
            True: 삭제 성공, False: 이미 없음
        """
        # 삭제 전 조회 (감사 로그용)
        existing = (
            await self.db.execute(
                select(MarketCalendar).where(
                    MarketCalendar.market == market,
                    MarketCalendar.holiday_date == target,
                )
            )
        ).scalar_one_or_none()
        if not existing:
            return False

        await self.db.execute(
            delete(MarketCalendar).where(
                MarketCalendar.market == market,
                MarketCalendar.holiday_date == target,
            )
        )
        await self.db.commit()
        await cache_delete(_cache_key(market, target.year))

        # 감사 로그 (구조화 로그)
        log.warning(
            "calendar_holiday_removed",
            date=target.isoformat(),
            name=existing.holiday_name,
            type=existing.holiday_type,
            market=market,
            actor_user_id=actor_user_id,
        )
        return True

    # ------------------------------------------------------------------
    # 동기화
    # ------------------------------------------------------------------
    async def sync_from_krx(self, year: int, market: str = "KRX") -> dict[str, int]:
        """pykrx 에서 휴장일을 받아 DB에 UPSERT 한다.

        - REGULAR 휴장일만 자동 동기화. TEMPORARY/SUBSTITUTE 는 보존.
        - pykrx 미설치 시 안전 fallback (시드 데이터 유지, 카운트 0 반환).
        - 결과 dict: {"fetched": N, "upserted": M, "skipped": K}.
        """
        try:
            holidays_raw = _fetch_pykrx_holidays(year)
        except _PykrxUnavailable as e:
            log.warning("pykrx_unavailable", year=year, reason=str(e))
            return {"fetched": 0, "upserted": 0, "skipped": 0}
        except Exception:
            log.exception("pykrx_fetch_failed", year=year)
            raise AppException("E0071", message="pykrx 휴장일 동기화 실패")

        upserted = 0
        skipped = 0
        for h in holidays_raw:
            # TEMPORARY 는 운영자 등록 영역이므로 자동 동기화 스킵
            if h.type == "TEMPORARY":
                skipped += 1
                continue
            stmt = pg_insert(MarketCalendar).values(
                holiday_date=h.date,
                holiday_name=h.name,
                holiday_type=h.type,
                market=market,
                source="pykrx",
                description=h.description,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["market", "holiday_date"],
                set_={
                    "holiday_name": stmt.excluded.holiday_name,
                    "holiday_type": stmt.excluded.holiday_type,
                    # 운영자가 manual 로 직접 입력한 항목은 source 를 manual 로 유지
                    "source": stmt.excluded.source,
                },
                # manual 로 입력된 항목은 보존 (source != 'manual' 일 때만 갱신)
                where=(MarketCalendar.source != "manual"),
            )
            await self.db.execute(stmt)
            upserted += 1
        await self.db.commit()

        # 해당 연도 캐시 무효화
        await cache_delete(_cache_key(market, year))

        log.info(
            "calendar_sync_done",
            year=year,
            market=market,
            fetched=len(holidays_raw),
            upserted=upserted,
            skipped=skipped,
        )
        return {"fetched": len(holidays_raw), "upserted": upserted, "skipped": skipped}

    # ------------------------------------------------------------------
    # 캐시 관리 (운영용)
    # ------------------------------------------------------------------
    async def invalidate_cache(self, year: int | None = None, market: str = "KRX") -> int:
        """캐시 무효화. year=None 이면 전체 캘린더 캐시 삭제.

        Returns: 삭제된 키 개수
        """
        if year is not None:
            await cache_delete(_cache_key(market, year))
            return 1
        # 패턴 삭제 (운영 빈도 낮음)
        redis = get_redis()
        pattern = f"{_CACHE_PREFIX}:{market}:*"
        deleted = 0
        async for key in redis.scan_iter(pattern):
            await redis.delete(key)
            deleted += 1
        return deleted


# ---------------------------------------------------------------------------
# pykrx 어댑터 (선택적 의존성)
# ---------------------------------------------------------------------------
class _PykrxUnavailable(RuntimeError):
    """pykrx 미설치 또는 호출 실패."""


def _fetch_pykrx_holidays(year: int) -> list[Holiday]:
    """pykrx 로 연간 휴장일을 가져온다.

    pykrx 는 직접적인 'holidays' API 가 없고, 영업일 캘린더(get_previous_business_day 등)와
    OHLCV 시계열에서 누락된 평일을 휴장일로 추정한다.

    1) 1/1 ~ 12/31 구간의 평일 목록 생성
    2) get_market_ohlcv_by_date('YYYYMMDD','YYYYMMDD','1001') 결과의 인덱스(거래일)와 차집합
       → 차집합이 휴장일 후보
    3) 각 후보의 한글 이름은 라이브러리에서 제공하지 않으므로 기본값 '휴장일' (운영자가 보정)
    """
    try:
        from pykrx import stock  # type: ignore[import-not-found]
    except Exception as e:  # pragma: no cover - 환경 의존
        raise _PykrxUnavailable(f"pykrx import 실패: {e}") from e

    start = f"{year}0101"
    end = f"{year}1231"
    try:
        # KOSPI 지수 (1001) 일봉으로 거래일 추출
        df = stock.get_index_ohlcv_by_date(start, end, "1001")  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover
        raise _PykrxUnavailable(f"pykrx OHLCV 조회 실패: {e}") from e

    trading_days: set[date] = set()
    try:
        for ts in df.index:
            trading_days.add(ts.date() if hasattr(ts, "date") else ts)
    except Exception:
        trading_days = set()

    # 1년치 평일 후보
    weekdays: list[date] = []
    cur = date(year, 1, 1)
    last = date(year, 12, 31)
    while cur <= last:
        if cur.weekday() < 5:
            weekdays.append(cur)
        cur = cur + timedelta(days=1)

    # 평일 - 거래일 = 휴장일 후보
    holidays: list[Holiday] = []
    for d in weekdays:
        if d in trading_days:
            continue
        holidays.append(
            Holiday(
                date=d,
                name="휴장일",  # pykrx 가 이름 제공 안 함 → 운영자가 sync 후 보정
                type="REGULAR",
                source="pykrx",
            )
        )
    return holidays


__all__ = ["CalendarService", "Holiday", "KST"]
