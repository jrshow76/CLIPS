"""종목/시세 도메인 스키마."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StockOut(BaseModel):
    """종목 메타."""

    code: str
    name: str
    market: str
    status: str = "LISTED"
    listing_shares: int | None = None
    market_cap: int | None = None
    listed_at: date | None = None


class StockSearchItem(BaseModel):
    """종목 검색 결과 아이템."""

    code: str
    name: str
    market: str
    sector: str | None = None


class QuoteOut(BaseModel):
    """실시간 시세."""

    code: str
    price: Decimal
    change: Decimal
    change_pct: Decimal
    volume: int
    ts: datetime


class OrderbookLevel(BaseModel):
    """호가 1단계."""

    price: Decimal
    qty: int


class OrderbookOut(BaseModel):
    """호가 10단계."""

    code: str
    asks: list[OrderbookLevel] = Field(default_factory=list)
    bids: list[OrderbookLevel] = Field(default_factory=list)
    ts: datetime


class CandleItem(BaseModel):
    """OHLCV 봉 1행."""

    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class FavoriteIn(BaseModel):
    """즐겨찾기 추가 요청."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=6)


class FavoriteItem(BaseModel):
    code: str
    name: str
    market: str
    created_at: datetime


CandleInterval = Literal["D", "W", "M", "1m", "5m", "15m", "30m", "60m"]
