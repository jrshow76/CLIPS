"""백테스트 스키마."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BacktestJobCreateIn(BaseModel):
    """POST /backtest/jobs."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    universe: list[str] = Field(default_factory=list)
    from_: str = Field(alias="from")
    to: str
    initial_capital: Decimal = Decimal("10000000")
    slippage: Decimal = Decimal("0.001")
    fee_rate: Decimal = Decimal("0.00015")


class BacktestJobOut(BaseModel):
    job_id: str
    status: str = "QUEUED"


class BacktestProgressOut(BaseModel):
    job_id: str
    status: str
    percent: int = 0
    eta_seconds: int | None = None


class BacktestTradeItem(BaseModel):
    code: str
    side: str
    entry_price: Decimal
    exit_price: Decimal | None = None
    qty: Decimal
    pnl: Decimal | None = None
    entry_at: datetime
    exit_at: datetime | None = None


class BacktestResultOut(BaseModel):
    job_id: str
    summary: dict[str, Any] = Field(default_factory=dict)
    equity_curve: dict[str, Any] | None = None
    trades: list[BacktestTradeItem] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class SaveResultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=100)


class SavedResultItem(BaseModel):
    run_id: int
    job_id: str
    label: str | None = None
    cumulative_return: Decimal | None = None
    annualized_return: Decimal | None = None
    mdd: Decimal | None = None
    sharpe: Decimal | None = None
    saved_at: datetime


class CompareIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_ids: list[str]
