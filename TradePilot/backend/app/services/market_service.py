"""시장 지수/캘린더 서비스."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.repositories.market_repository import MarketIndexRepository

KST = ZoneInfo("Asia/Seoul")


# 한국 증시 휴장일 (간이 데이터: 2026년 일부)
KR_HOLIDAYS: dict[int, list[tuple[date, str]]] = {
    2026: [
        (date(2026, 1, 1), "신정"),
        (date(2026, 2, 16), "설날 대체"),
        (date(2026, 2, 17), "설날"),
        (date(2026, 2, 18), "설날"),
        (date(2026, 3, 1), "삼일절"),
        (date(2026, 5, 5), "어린이날"),
        (date(2026, 5, 25), "석가탄신일"),
        (date(2026, 6, 6), "현충일"),
        (date(2026, 8, 15), "광복절"),
        (date(2026, 9, 24), "추석"),
        (date(2026, 9, 25), "추석"),
        (date(2026, 9, 26), "추석"),
        (date(2026, 10, 3), "개천절"),
        (date(2026, 10, 9), "한글날"),
        (date(2026, 12, 25), "크리스마스"),
        (date(2026, 12, 31), "연말 휴장"),
    ]
}


class MarketService:
    """시장 지수/캘린더 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MarketIndexRepository(db)

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

    def market_status(self, *, ref: datetime | None = None) -> dict[str, Any]:
        """현재 장 운영 상태.

        - 오전 09:00 ~ 15:30 KST: OPEN
        - 11:30 ~ 13:00 점심 BREAK 미적용 (코스피 단일가)
        - 08:00 ~ 09:00: PRE
        - 그 외: CLOSED
        """
        now = ref or datetime.now(tz=KST)
        if now.tzinfo is None:
            now = now.replace(tzinfo=KST)
        today = now.date()
        is_holiday = self._is_holiday(today) or now.weekday() >= 5

        open_t = time(9, 0)
        close_t = time(15, 30)
        pre_t = time(8, 0)

        if is_holiday:
            session: str = "CLOSED"
        else:
            t = now.time()
            if pre_t <= t < open_t:
                session = "PRE"
            elif open_t <= t <= close_t:
                session = "OPEN"
            else:
                session = "CLOSED"

        next_open = self._next_open(today, now)
        return {"session": session, "next_open": next_open, "holiday": is_holiday}

    def calendar(self, year: int) -> list[dict[str, Any]]:
        """연간 휴장일 캘린더."""
        if year not in KR_HOLIDAYS:
            return []
        items = [
            {"date": d, "is_open": False, "name": name}
            for d, name in KR_HOLIDAYS[year]
        ]
        return items

    def _is_holiday(self, d: date) -> bool:
        return any(h[0] == d for h in KR_HOLIDAYS.get(d.year, []))

    def _next_open(self, today: date, now: datetime) -> datetime | None:
        """다음 개장 시각 KST."""
        candidate = today
        # 오늘 장 시작 전이면 오늘 09:00
        if not (self._is_holiday(candidate) or candidate.weekday() >= 5):
            if now.time() < time(9, 0):
                return datetime.combine(candidate, time(9, 0), tzinfo=KST)
        # 다음 영업일
        for _ in range(1, 15):
            candidate = candidate + timedelta(days=1)
            if self._is_holiday(candidate) or candidate.weekday() >= 5:
                continue
            return datetime.combine(candidate, time(9, 0), tzinfo=KST)
        return None
