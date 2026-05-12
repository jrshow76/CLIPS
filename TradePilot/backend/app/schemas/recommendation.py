"""추천주 스키마."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    """추천주 페이지 아이템."""

    id: str
    code: str
    name: str
    score: Decimal
    reason_code: str | None = None
    reason: str | None = None
    current_price: Decimal | None = None
    change_pct: Decimal | None = None
    trade_date: date


class TopRecommendation(BaseModel):
    code: str
    name: str
    score: Decimal
    reason_code: str | None = None


class RecommendationDetail(BaseModel):
    code: str
    name: str
    score: Decimal
    reason_code: str | None = None
    reason: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    indicators: dict[str, Any] = Field(default_factory=dict)
    ml_prediction: dict[str, Any] | None = None


class StrategyMetaItem(BaseModel):
    """추천 생성에 사용된 전략 메타."""

    id: str
    name: str
    description: str | None = None
