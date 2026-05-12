"""ML 예측 스키마."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PredictionPoint(BaseModel):
    date: date
    mean: Decimal
    lower: Decimal
    upper: Decimal


class PredictionOut(BaseModel):
    code: str
    predictions: list[PredictionPoint] = Field(default_factory=list)
    model_version: str | None = None


class AccuracyOut(BaseModel):
    code: str
    period: str
    mape: Decimal | None = None
    direction_accuracy: Decimal | None = None


class RetrainIn(BaseModel):
    """POST /ml-predictions/retrain."""

    model_config = ConfigDict(extra="forbid")

    codes: list[str] | None = None
    full: bool = False


class RetrainOut(BaseModel):
    job_id: str
    status: str = "QUEUED"


class TrainingJobStatusOut(BaseModel):
    job_id: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
