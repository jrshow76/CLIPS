"""TradePilot ML 엔진.

외부에 노출하는 API:
    - MLConfig
    - 단일 종목 학습/추론: train_model, predict_from_ohlcv, load_model
    - 멀티 종목 학습: train_sector_model, train_multistock_model
    - 앙상블/자동 선택 추론: predict_ensemble, predict_auto
    - 레지스트리: list_models / list_available_models / get_model_meta
                  / model_exists / sector_model_exists / global_model_exists
                  / get_model_for_stock

torch / sklearn 등은 lazy import 로 처리하므로, 의존성 미설치 환경에서도
본 모듈 import 자체는 통과한다 (실제 호출 시 ImportError 발생).
"""
from app.services.ml_engine.config import (
    DEFAULT_DOWN_THRESHOLD,
    DEFAULT_FEATURES,
    DEFAULT_UP_THRESHOLD,
    MLConfig,
)
from app.services.ml_engine.predictor import (
    DIRECTION_LABELS,
    EnsembleResult,
    PredictionResult,
    load_model,
    load_multi_model,
    predict_auto,
    predict_ensemble,
    predict_from_ohlcv,
    predict_with_model,
    predictions_to_ml_record,
)
from app.services.ml_engine.registry import (
    FRESH_INDIVIDUAL_DAYS,
    ModelKind,
    ModelMeta,
    get_model_dir,
    get_model_for_stock,
    get_model_meta,
    global_model_exists,
    list_available_models,
    list_models,
    model_exists,
    sector_model_exists,
)
from app.services.ml_engine.trainer import (
    MultiStockTrainResult,
    TrainResult,
    train_model,
    train_multistock_model,
    train_sector_model,
)

__all__ = [
    # config
    "MLConfig",
    "DEFAULT_FEATURES",
    "DEFAULT_UP_THRESHOLD",
    "DEFAULT_DOWN_THRESHOLD",
    # trainer (단일)
    "TrainResult",
    "train_model",
    # trainer (멀티)
    "MultiStockTrainResult",
    "train_sector_model",
    "train_multistock_model",
    # predictor
    "PredictionResult",
    "EnsembleResult",
    "DIRECTION_LABELS",
    "predict_from_ohlcv",
    "predict_with_model",
    "predict_auto",
    "predict_ensemble",
    "load_model",
    "load_multi_model",
    "predictions_to_ml_record",
    # registry
    "ModelKind",
    "ModelMeta",
    "FRESH_INDIVIDUAL_DAYS",
    "list_models",
    "list_available_models",
    "get_model_meta",
    "get_model_for_stock",
    "model_exists",
    "sector_model_exists",
    "global_model_exists",
    "get_model_dir",
]
