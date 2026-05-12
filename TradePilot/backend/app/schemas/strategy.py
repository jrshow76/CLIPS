"""전략 도메인 스키마."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrategyCreateIn(BaseModel):
    """POST /strategies."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    entry_rules: dict[str, Any] = Field(default_factory=dict)
    exit_rules: dict[str, Any] = Field(default_factory=dict)
    universe: list[Any] = Field(default_factory=list)
    limits: dict[str, Any] = Field(default_factory=dict)


class StrategyUpdateIn(BaseModel):
    """PATCH /strategies/{id}."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    entry_rules: dict[str, Any] | None = None
    exit_rules: dict[str, Any] | None = None
    universe: list[Any] | None = None
    limits: dict[str, Any] | None = None


class StrategyOut(BaseModel):
    id: str  # public_id
    name: str
    description: str | None = None
    entry_rules: dict[str, Any] = Field(default_factory=dict)
    exit_rules: dict[str, Any] = Field(default_factory=dict)
    universe: list[Any] = Field(default_factory=list)
    limits: dict[str, Any] = Field(default_factory=dict)
    active: bool = False
    activated_at: datetime | None = None
    deactivated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class StrategyActivateIn(BaseModel):
    """PATCH /strategies/{id}/activate."""

    model_config = ConfigDict(extra="forbid")

    active: bool
    otp_token: str | None = None


class StrategyPerformanceOut(BaseModel):
    id: str
    period: str
    trades: int
    win_rate: float | None = None
    cumulative_return: float | None = None
    mdd: float | None = None
