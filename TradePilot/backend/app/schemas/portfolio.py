"""포트폴리오 스키마."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class PortfolioSummaryOut(BaseModel):
    total_value: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")
    equity: Decimal = Decimal("0")
    daily_pnl: Decimal = Decimal("0")
    daily_pnl_pct: Decimal = Decimal("0")
    position_count: int = 0


class PositionItem(BaseModel):
    code: str
    name: str
    qty: Decimal
    avg_price: Decimal
    current_price: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    realized_pnl: Decimal = Decimal("0")
    trade_mode: Literal["SIM", "LIVE"]


class HistorySeriesPoint(BaseModel):
    ts: date
    cash: Decimal
    equity: Decimal
    total_value: Decimal


class RealizedPnlItem(BaseModel):
    trade_date: date
    realized_pnl: Decimal
    win_count: int
    loss_count: int


class RealizedPnlSummary(BaseModel):
    total_pnl: Decimal = Decimal("0")
    win_count: int = 0
    loss_count: int = 0
    win_rate: float = 0.0
    items: list[RealizedPnlItem] = Field(default_factory=list)
