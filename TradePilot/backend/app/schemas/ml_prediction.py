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
    """POST /ml/predict 요청.

    ensemble=True (기본) 인 경우 동기 추론으로 즉시 앙상블 결과를 반환한다.
    ensemble=False 인 경우 기존 비동기 단일 모델 추론 (prediction_id 폴링).
    """

    model_config = ConfigDict(extra="forbid")

    stock_code: str = Field(..., min_length=4, max_length=10)
    horizon: Literal[1, 3, 5] = 1
    ensemble: bool = True
    sector_code: str | None = None


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


# ============================================================================
# 멀티 종목 모델 API
# ============================================================================
class PredictEnsembleRequestIn(BaseModel):
    """POST /ml/predict (ensemble) 요청."""

    model_config = ConfigDict(extra="forbid")

    stock_code: str = Field(..., min_length=4, max_length=10)
    horizon: Literal[1, 3, 5] = 1
    ensemble: bool = True                 # True 면 앙상블, False 면 단일 자동 선택
    sector_code: str | None = None        # 섹터 모델 사용 시 코드


class EnsembleContribution(BaseModel):
    """모델별 기여도."""

    model_key: str
    prob_down: float
    prob_flat: float
    prob_up: float
    weight: float


class EnsembleResultOut(BaseModel):
    """앙상블 결과."""

    stock_code: str
    horizon: int
    direction: Literal["UP", "FLAT", "DOWN"]
    confidence: float
    prob_up: float
    prob_flat: float
    prob_down: float
    asof_date: date | None = None
    used_kinds: list[str] = Field(default_factory=list)
    contributions: dict[str, EnsembleContribution] = Field(default_factory=dict)


class ModelCatalogItem(BaseModel):
    """/ml/models 카탈로그 아이템."""

    model_key: str
    kind: Literal["INDIVIDUAL", "SECTOR", "GLOBAL"]
    stock_code: str | None = None
    identifier: str | None = None
    horizon_days: int
    lookback_days: int
    features: list[str] = Field(default_factory=list)
    best_val_acc: float | None = None
    best_val_f1: float | None = None
    trained_at: str | None = None
    model_param_count: int | None = None
    num_stocks: int = 1


class ModelCatalogOut(BaseModel):
    """모델 카탈로그 응답."""

    individual: list[ModelCatalogItem] = Field(default_factory=list)
    sector: list[ModelCatalogItem] = Field(default_factory=list)
    global_: list[ModelCatalogItem] = Field(default_factory=list, alias="global")

    model_config = ConfigDict(populate_by_name=True)


class TrainSectorIn(BaseModel):
    """POST /ml/train/sector/{sector_code} 요청."""

    model_config = ConfigDict(extra="forbid")

    stock_codes: list[str] | None = None  # None 이면 DB 에서 자동 조회
    horizon: Literal[1, 3, 5] = 1
    config: dict[str, Any] | None = None


class TrainGlobalIn(BaseModel):
    """POST /ml/train/global 요청."""

    model_config = ConfigDict(extra="forbid")

    stock_codes: list[str] | None = None  # None 이면 전 활성 종목
    horizon: Literal[1, 3, 5] = 1
    config: dict[str, Any] | None = None


class ModelComparisonOut(BaseModel):
    """모델별 예측 비교 (디버그용)."""

    stock_code: str
    horizon: int
    individual: EnsembleContribution | None = None
    sector: EnsembleContribution | None = None
    global_: EnsembleContribution | None = Field(default=None, alias="global")
    ensemble: EnsembleResultOut | None = None

    model_config = ConfigDict(populate_by_name=True)
