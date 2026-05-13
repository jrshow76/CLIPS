"""CalendarService 단위 테스트.

DB 의존을 제거하기 위해 in-memory 가짜 세션과 Redis 더블을 사용한다.
실제 DDL/SQL 검증은 통합 테스트에서 수행한다.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.services.calendar_service import CalendarService, Holiday

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# In-memory 휴장일 저장소를 사용하는 가짜 CalendarService 서브클래스
# ---------------------------------------------------------------------------
class FakeCalendarService(CalendarService):
    """DB / Redis 의존을 제거하고 메모리 dict 만으로 동작."""

    def __init__(self, seed: list[Holiday] | None = None) -> None:
        # 부모 __init__ 호출 안 함 (db / redis 미사용)
        self._store: dict[tuple[str, date], Holiday] = {}
        for h in seed or []:
            self._store[(h.market, h.date)] = h

    async def get_holidays(self, year: int, market: str = "KRX") -> list[Holiday]:
        return sorted(
            (h for (m, d), h in self._store.items() if m == market and d.year == year),
            key=lambda h: h.date,
        )

    async def add_holiday(  # type: ignore[override]
        self,
        target: date,
        name: str,
        holiday_type: str = "TEMPORARY",
        *,
        market: str = "KRX",
        source: str = "manual",
        description: str | None = None,
    ) -> Holiday:
        h = Holiday(
            date=target,
            name=name,
            type=holiday_type,
            market=market,
            source=source,
            description=description,
        )
        self._store[(market, target)] = h
        return h

    async def remove_holiday(  # type: ignore[override]
        self,
        target: date,
        market: str = "KRX",
        *,
        actor_user_id: int | None = None,
    ) -> bool:
        key = (market, target)
        if key in self._store:
            del self._store[key]
            return True
        return False


def _seed_2026_holidays() -> list[Holiday]:
    """init/16_calendar_seed.sql 의 2026년 시드 데이터를 그대로 재구성."""
    raw = [
        ("2026-01-01", "신정", "REGULAR"),
        ("2026-02-16", "설날 연휴", "REGULAR"),
        ("2026-02-17", "설날", "REGULAR"),
        ("2026-02-18", "설날 연휴", "REGULAR"),
        ("2026-03-02", "삼일절 대체공휴일", "SUBSTITUTE"),
        ("2026-05-01", "근로자의 날", "REGULAR"),
        ("2026-05-05", "어린이날", "REGULAR"),
        ("2026-05-25", "부처님오신날", "REGULAR"),
        ("2026-06-03", "지방선거일", "TEMPORARY"),
        ("2026-08-17", "광복절 대체공휴일", "SUBSTITUTE"),
        ("2026-09-24", "추석 연휴", "REGULAR"),
        ("2026-09-25", "추석", "REGULAR"),
        ("2026-10-05", "개천절 대체공휴일", "SUBSTITUTE"),
        ("2026-10-09", "한글날", "REGULAR"),
        ("2026-12-25", "성탄절", "REGULAR"),
        ("2026-12-31", "연말 휴장일", "REGULAR"),
    ]
    return [
        Holiday(date=date.fromisoformat(d), name=n, type=t, source="seed") for d, n, t in raw
    ]


# ---------------------------------------------------------------------------
# 테스트
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_2026_seed_contains_major_holidays() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    holidays = await svc.get_holidays(2026)
    names = [h.name for h in holidays]
    # 신정 / 설날 / 추석 / 한글날 / 크리스마스 / 연말
    assert any("신정" in n for n in names)
    assert any("설날" in n for n in names)
    assert any("추석" in n for n in names)
    assert "한글날" in names
    assert "성탄절" in names
    assert any("연말" in n for n in names)


@pytest.mark.asyncio
async def test_is_holiday_true_for_seoul_new_year() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    assert await svc.is_holiday(date(2026, 1, 1)) is True
    assert await svc.is_holiday(date(2026, 1, 2)) is False  # 평일이지만 휴장 아님


@pytest.mark.asyncio
async def test_is_business_day_excludes_weekend_and_holiday() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    # 2026-01-03 은 토요일
    assert await svc.is_business_day(date(2026, 1, 3)) is False
    # 2026-01-04 은 일요일
    assert await svc.is_business_day(date(2026, 1, 4)) is False
    # 2026-01-05 월요일 (영업일)
    assert await svc.is_business_day(date(2026, 1, 5)) is True
    # 휴장일
    assert await svc.is_business_day(date(2026, 1, 1)) is False


@pytest.mark.asyncio
async def test_next_business_day_skips_weekend() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    # 2026-01-02(금) 다음 영업일 → 2026-01-05(월)
    assert await svc.next_business_day(date(2026, 1, 2)) == date(2026, 1, 5)


@pytest.mark.asyncio
async def test_next_business_day_skips_seollal_holiday_block() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    # 2026-02-13(금) 다음 영업일은 설날 연휴(2/16~18)를 건너뛴 2/19(목)
    nxt = await svc.next_business_day(date(2026, 2, 13))
    assert nxt == date(2026, 2, 19)


@pytest.mark.asyncio
async def test_previous_business_day_skips_weekend() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    # 2026-01-05(월) 이전 영업일 → 2026-01-02(금) (1/1 신정 휴장)
    assert await svc.previous_business_day(date(2026, 1, 5)) == date(2026, 1, 2)


@pytest.mark.asyncio
async def test_business_days_between_short_range() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    # 2026-01-01(목, 휴장) ~ 2026-01-09(금)
    # 평일: 1/1(휴), 1/2(영), 1/5(영), 1/6(영), 1/7(영), 1/8(영), 1/9(영) → 6
    cnt = await svc.business_days_between(date(2026, 1, 1), date(2026, 1, 9))
    assert cnt == 6


@pytest.mark.asyncio
async def test_business_days_between_inverted_returns_zero() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    cnt = await svc.business_days_between(date(2026, 1, 10), date(2026, 1, 1))
    assert cnt == 0


@pytest.mark.asyncio
async def test_add_temporary_holiday_then_is_holiday_true() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    target = date(2026, 4, 15)  # 평일
    assert await svc.is_holiday(target) is False
    await svc.add_holiday(target, name="임시휴장(시스템 점검)", holiday_type="TEMPORARY")
    assert await svc.is_holiday(target) is True
    # 영업일 판정도 갱신
    assert await svc.is_business_day(target) is False


@pytest.mark.asyncio
async def test_remove_holiday_returns_true_then_false() -> None:
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    target = date(2026, 1, 1)
    assert await svc.remove_holiday(target) is True
    assert await svc.is_holiday(target) is False
    # 두 번째는 false
    assert await svc.remove_holiday(target) is False


@pytest.mark.asyncio
async def test_holiday_type_constants_only_allowed_values() -> None:
    """REGULAR/TEMPORARY/SUBSTITUTE 만 허용되는지 확인 (FakeService 는 검증 생략하므로 실제 svc 호출)."""
    from app.core.exceptions import AppException

    class MinimalSvc(CalendarService):
        def __init__(self) -> None:
            pass  # db 없음

    svc = MinimalSvc()
    with pytest.raises(AppException) as exc:
        await svc.add_holiday(date(2026, 7, 1), "잘못된타입", holiday_type="WRONG")
    assert exc.value.code == "E0003"


@pytest.mark.asyncio
async def test_seed_2026_holidays_count() -> None:
    """시드 2026 휴장일은 16건."""
    svc = FakeCalendarService(seed=_seed_2026_holidays())
    holidays = await svc.get_holidays(2026)
    assert len(holidays) == 16
