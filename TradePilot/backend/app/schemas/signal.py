"""시그널 도메인 스키마."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SignalStatus = Literal["ACTIVE", "EXECUTED", "IGNORED", "EXPIRED"]
SignalAction = Literal["BUY", "SELL"]


class SignalItem(BaseModel):
    """시그널 페이지 아이템."""

    id: str  # public_id
    code: str
    action: SignalAction
    price: Decimal | None = None
    confidence: str = "MID"
    status: SignalStatus
    created_at: datetime


class SignalDetail(BaseModel):
    id: str
    code: str
    strategy_id: str | None = None
    action: SignalAction
    confidence: str
    trigger_price: Decimal | None = None
    status: SignalStatus
    condition_trace: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    expires_at: datetime | None = None


class SignalCountOut(BaseModel):
    active: int
    today: int
    ignored: int


class SignalTestIn(BaseModel):
    """POST /signals/test (ADMIN)."""

    model_config = ConfigDict(extra="forbid")

    strategy_id: str
    code: str = Field(min_length=6, max_length=6)
