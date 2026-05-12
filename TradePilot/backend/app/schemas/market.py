"""시장(지수) 스키마."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


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
    date: date
    is_open: bool
    name: str | None = None
