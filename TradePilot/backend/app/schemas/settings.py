"""사용자 설정/한도/모드 전환 스키마."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TradeModeOut(BaseModel):
    mode: Literal["SIM", "LIVE"]
    switched_at: datetime | None = None


class TradeModeSwitchIn(BaseModel):
    """POST /settings/trade-mode/switch."""

    model_config = ConfigDict(extra="forbid")

    target: Literal["SIM", "LIVE"]
    otp_token: str | None = None
    terms_token: str | None = None


class RiskLimitOut(BaseModel):
    daily_buy_amount: Decimal
    daily_buy_count: int
    per_stock_amount: Decimal
    max_positions: int
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    daily_loss_limit_pct: Decimal
    single_order_max_qty: int


class RiskLimitUpdateIn(BaseModel):
    """PUT /settings/risk-limits."""

    model_config = ConfigDict(extra="forbid")

    daily_buy_amount: Decimal | None = None
    daily_buy_count: int | None = Field(default=None, ge=1, le=1000)
    per_stock_amount: Decimal | None = None
    max_positions: int | None = Field(default=None, ge=1, le=100)
    stop_loss_pct: Decimal | None = None
    take_profit_pct: Decimal | None = None
    daily_loss_limit_pct: Decimal | None = None
    single_order_max_qty: int | None = Field(default=None, ge=1, le=100000)


class KillSwitchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class CreonStatusOut(BaseModel):
    connected: bool
    account_masked: str | None = None
    last_check_at: datetime | None = None


class CreonTestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_token: str


class ScheduleOut(BaseModel):
    """사용자 스케줄 설정."""

    market_hours_only: bool = True
    pre_market_start: str = "08:30"
    post_market_end: str = "16:00"
    auto_kill_switch_loss_pct: Decimal | None = None


class ScheduleUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_hours_only: bool | None = None
    pre_market_start: str | None = None
    post_market_end: str | None = None
    auto_kill_switch_loss_pct: Decimal | None = None
