"""시장(지수/캘린더) 스키마."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class IndexItem(BaseModel):
    code: str
    name: str
    value: Decimal
    change: Decimal
    change_pct: Decimal
    ts: datetime


class IndexCandle(BaseModel):
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class MarketStatusOut(BaseModel):
    session: Literal["PRE", "OPEN", "BREAK", "CLOSED"]
    next_open: datetime | None = None
    holiday: bool = False


class CalendarItem(BaseModel):
    """레거시 캘린더 응답 (yes/no 형태)."""

    date: date
    is_open: bool
    name: str | None = None


# ---------------------------------------------------------------------------
# 신규 캘린더 스키마
# ---------------------------------------------------------------------------
class CalendarHolidayItem(BaseModel):
    """휴장일 상세 응답."""

    holiday_date: date
    holiday_name: str
    holiday_type: Literal["REGULAR", "TEMPORARY", "SUBSTITUTE"]
    market: str = "KRX"
    source: Literal["pykrx", "manual", "seed"] = "pykrx"
    description: str | None = None


class BusinessDayOut(BaseModel):
    """영업일 판정 응답."""

    date: date
    is_business_day: bool
    is_holiday: bool
    is_weekend: bool
    next_business_day: date
    previous_business_day: date


class HolidayCreateIn(BaseModel):
    """관리자 - 휴장일 추가 요청."""

    holiday_date: date
    holiday_name: str = Field(..., min_length=1, max_length=100)
    holiday_type: Literal["REGULAR", "TEMPORARY", "SUBSTITUTE"] = "TEMPORARY"
    market: str = Field("KRX", min_length=2, max_length=10)
    description: str | None = None


class CalendarSyncOut(BaseModel):
    """관리자 - 동기화 결과 응답 (인라인 fallback 시)."""

    year: int
    fetched: int
    upserted: int
    skipped: int
