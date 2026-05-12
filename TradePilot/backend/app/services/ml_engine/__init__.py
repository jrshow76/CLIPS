"""TradePilot ML 엔진.

외부에 노출하는 API:
    - MLConfig
    - train_model
    - predict_from_ohlcv (OHLCV 직접 입력 추론)
    - load_model
    - list_models / get_model_meta / model_exists (registry)

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
    PredictionResult,
    load_model,
    predict_from_ohlcv,
    predictions_to_ml_record,
)
from app.services.ml_engine.registry import (
    ModelMeta,
    get_model_dir,
    get_model_meta,
    list_models,
    model_exists,
)
from app.services.ml_engine.trainer import TrainResult, train_model

__all__ = [
    # config
    "MLConfig",
    "DEFAULT_FEATURES",
    "DEFAULT_UP_THRESHOLD",
    "DEFAULT_DOWN_THRESHOLD",
    # trainer
    "TrainResult",
    "train_model",
    # predictor
    "PredictionResult",
    "DIRECTION_LABELS",
    "predict_from_ohlcv",
    "load_model",
    "predictions_to_ml_record",
    # registry
    "ModelMeta",
    "list_models",
    "get_model_meta",
    "model_exists",
    "get_model_dir",
]
