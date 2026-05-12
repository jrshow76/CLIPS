"""리포트 도메인 스키마."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PnlSeriesItem(BaseModel):
    ts: date
    realized: Decimal
    unrealized: Decimal
    total: Decimal


class PnlReportOut(BaseModel):
    granularity: str
    series: list[PnlSeriesItem] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class PositionReportItem(BaseModel):
    code: str
    name: str
    realized_pnl: Decimal
    win_count: int
    loss_count: int


class TradeReportItem(BaseModel):
    id: str
    code: str
    side: str
    qty: Decimal
    price: Decimal | None = None
    status: str
    created_at: datetime
    filled_at: datetime | None = None


class StrategyReportItem(BaseModel):
    strategy_id: str
    name: str
    trades: int
    win_rate: float | None = None
    cumulative_return: float | None = None


class ExportRequestIn(BaseModel):
    """POST /reports/export."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["pnl", "positions", "trades", "strategies"]
    from_: str = Field(alias="from")
    to: str
    format: Literal["csv", "xlsx"] = "csv"


class ExportJobOut(BaseModel):
    export_id: str
    status: str = "QUEUED"


class ExportStatusOut(BaseModel):
    export_id: str
    status: str
    download_url: str | None = None
    expires_at: datetime | None = None
