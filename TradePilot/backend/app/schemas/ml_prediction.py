"""ML 예측 스키마."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Legacy: 회귀형 응답
# ============================================================================
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


# ============================================================================
# 신규: 3-class 분류 API
# ============================================================================
class PredictRequestIn(BaseModel):
    """POST /ml/predict 요청."""

    model_config = ConfigDict(extra="forbid")

    stock_code: str = Field(..., min_length=4, max_length=10)
    horizon: Literal[1, 3, 5] = 1


class PredictAcceptedOut(BaseModel):
    """추론 요청 수락 응답 (비동기 폴링용)."""

    prediction_id: str
    status: Literal["QUEUED", "DONE"]
    cached: bool = False


class PredictionResultOut(BaseModel):
    """GET /ml/predictions/{id} 폴링 결과."""

    prediction_id: str
    status: str  # QUEUED / RUNNING / DONE / FAILED / UNKNOWN
    direction: Literal["UP", "FLAT", "DOWN"] | None = None
    confidence: float | None = None
    prob_up: float | None = None
    prob_flat: float | None = None
    prob_down: float | None = None
    model_key: str | None = None
    asof_date: date | None = None
    horizon: int | None = None
    error: str | None = None


class PredictionListItem(BaseModel):
    """GET /ml/predictions 목록 아이템."""

    id: int | None = None
    code: str
    base_date: date | None = None
    horizon: int
    pred_mean: float | None = None
    pred_lower: float | None = None
    pred_upper: float | None = None
    model_version: str | None = None
    direction_acc: float | None = None
    created_at: datetime | None = None


class TrainRequestIn(BaseModel):
    """POST /ml/train 요청 (관리자)."""

    model_config = ConfigDict(extra="forbid")

    stock_code: str = Field(..., min_length=4, max_length=10)
    horizon: Literal[1, 3, 5] = 1
    config: dict[str, Any] | None = None  # MLConfig 오버라이드


class TrainAcceptedOut(BaseModel):
    job_id: str
    status: Literal["QUEUED"] = "QUEUED"


class TrainStatusOut(BaseModel):
    """GET /ml/train/{job_id} 상태."""

    job_id: str
    status: str
    progress: int | None = None
    stock_code: str | None = None
    horizon: int | None = None
    best_val_loss: float | None = None
    best_val_acc: float | None = None
    best_val_f1: float | None = None
    epochs_run: int | None = None
    duration_sec: float | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
