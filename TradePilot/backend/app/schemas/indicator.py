"""지표 응답 스키마."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

IndicatorInterval = Literal["D", "W", "M", "1m", "5m", "15m", "30m", "60m"]


class MaSeriesOut(BaseModel):
    """이동평균 응답."""

    code: str
    interval: str
    periods: dict[str, list[float | None]] = Field(default_factory=dict)


class RsiSeriesOut(BaseModel):
    code: str
    interval: str
    period: int
    values: list[float | None]


class MacdSeriesOut(BaseModel):
    code: str
    interval: str
    macd: list[float | None]
    signal: list[float | None]
    hist: list[float | None]


class BollingerSeriesOut(BaseModel):
    code: str
    interval: str
    mid: list[float | None]
    upper: list[float | None]
    lower: list[float | None]


class SimpleSeriesOut(BaseModel):
    code: str
    interval: str
    values: list[float | None]


class StochasticSeriesOut(BaseModel):
    code: str
    interval: str
    k: list[float | None]
    d: list[float | None]


class IndicatorBatchIn(BaseModel):
    """POST /indicators/batch 요청."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=6)
    interval: IndicatorInterval = "D"
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    indicators: list[dict[str, Any]] = Field(default_factory=list)


class IndicatorBatchOut(BaseModel):
    code: str
    interval: str
    results: dict[str, Any] = Field(default_factory=dict)
