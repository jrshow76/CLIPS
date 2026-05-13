"""시장 지수/캘린더 서비스.

휴장일 데이터는 `tp_market.market_calendar` 테이블을 단일 소스로 사용한다.
모든 휴장/영업일 판정은 `app.services.calendar_service.CalendarService` 로 위임한다.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.repositories.market_repository import MarketIndexRepository
from app.services.calendar_service import CalendarService

KST = ZoneInfo("Asia/Seoul")


class MarketService:
    """시장 지수/캘린더 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MarketIndexRepository(db)
        self.calendar_svc = CalendarService(db)

    async def list_indices(self) -> list[dict[str, Any]]:
        idxs = await self.repo.list_all()
        out: list[dict[str, Any]] = []
        for idx in idxs:
            d = await self.repo.latest_daily(idx.id)
            if not d:
                continue
            out.append(
                {
                    "code": idx.code,
                    "name": idx.name,
                    "value": d.close,
                    "change": Decimal(str(float(d.close) - float(d.open))),
                    "change_pct": d.change_pct or Decimal("0"),
                    "ts": datetime.combine(d.trade_date, datetime.min.time()),
                }
            )
        return out

    async def candles(
        self,
        code: str,
        *,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        idx = await self.repo.find_by_code(code)
        if not idx:
            raise AppException("E0062", message="지수를 찾을 수 없습니다.")
        rows = await self.repo.list_daily(idx.id, from_date=from_date, to_date=to_date)
        return [
            {
                "ts": datetime.combine(r.trade_date, datetime.min.time()),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": int(r.volume),
            }
            for r in rows
        ]

    async def market_status(self, *, ref: datetime | None = None) -> dict[str, Any]:
        """현재 장 운영 상태 (KST).

        - 오전 09:00 ~ 15:30 KST: OPEN
        - 11:30 ~ 13:00 점심 BREAK 미적용 (코스피 단일가)
        - 08:00 ~ 09:00: PRE
        - 그 외: CLOSED
        - 주말 또는 휴장일: CLOSED
        """
        now = ref or datetime.now(tz=KST)
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        today = now.date()

        # 휴장 여부 (DB)
        is_holiday_db = await self.calendar_svc.is_holiday(today)
        is_weekend = now.weekday() >= 5
        is_closed_today = is_holiday_db or is_weekend

        open_t = time(9, 0)
        close_t = time(15, 30)
        pre_t = time(8, 0)

        if is_closed_today:
            session: str = "CLOSED"
        else:
            t = now.time()
            if pre_t <= t < open_t:
                session = "PRE"
            elif open_t <= t <= close_t:
                session = "OPEN"
            else:
                session = "CLOSED"

        next_open = await self._next_open(today, now)
        return {"session": session, "next_open": next_open, "holiday": is_holiday_db}

    async def calendar(self, year: int) -> list[dict[str, Any]]:
        """연간 휴장일 캘린더."""
        holidays = await self.calendar_svc.get_holidays(year)
        return [
            {"date": h.date, "is_open": False, "name": h.name}
            for h in holidays
        ]

    async def _next_open(self, today: date, now: datetime) -> datetime | None:
        """다음 개장 시각 KST."""
        # 오늘이 영업일이고 장 시작 전이면 오늘 09:00
        if await self.calendar_svc.is_business_day(today):
            if now.time() < time(9, 0):
                return datetime.combine(today, time(9, 0), tzinfo=KST)
        # 다음 영업일 09:00
        try:
            nxt = await self.calendar_svc.next_business_day(today)
        except AppException:
            return None
        return datetime.combine(nxt, time(9, 0), tzinfo=KST)
