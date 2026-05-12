"""추론 모듈.

학습된 모델/스케일러를 디스크에서 로드하여 단건 추론을 수행한다.

`predict_from_ohlcv(df, config)` 가 핵심 API.
`predict(...)` 는 DB 로드까지 포함한 비동기 변형.

추론 결과 형식:
    {
        "direction": "UP" | "FLAT" | "DOWN",
        "confidence": float (예측 클래스의 확률),
        "prob_up":   float,
        "prob_flat": float,
        "prob_down": float,
        "model_key": str,
        "asof_date": ISO date,
    }
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog

from app.services.ml_engine.config import MLConfig
from app.services.ml_engine.dataset import apply_scaler
from app.services.ml_engine.features import build_features
from app.services.ml_engine.model import build_model

log = structlog.get_logger(__name__)

DIRECTION_LABELS = ("DOWN", "FLAT", "UP")  # class 0, 1, 2


@dataclass
class PredictionResult:
    """추론 결과."""

    direction: str
    confidence: float
    prob_down: float
    prob_flat: float
    prob_up: float
    model_key: str
    asof_date: date
    horizon_days: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "prob_down": self.prob_down,
            "prob_flat": self.prob_flat,
            "prob_up": self.prob_up,
            "model_key": self.model_key,
            "asof_date": self.asof_date.isoformat(),
            "horizon_days": self.horizon_days,
        }


def _import_torch():
    try:
        import torch
        return torch
    except ImportError as e:  # pragma: no cover
        raise ImportError("PyTorch 가 설치되어 있지 않습니다.") from e


def load_model(model_dir: str, config: MLConfig | None = None) -> tuple[Any, Any, dict[str, Any]]:
    """저장된 모델/스케일러/메타 로드.

    Args:
        model_dir: {ML_MODEL_DIR}/{model_key} 절대경로
        config: None 이면 meta.json 으로부터 재구성

    Returns:
        (model, scaler, meta)
    """
    torch = _import_torch()
    import joblib

    meta_path = os.path.join(model_dir, "meta.json")
    state_path = os.path.join(model_dir, "model.pt")
    scaler_path = os.path.join(model_dir, "scaler.joblib")

    if not (os.path.exists(meta_path) and os.path.exists(state_path) and os.path.exists(scaler_path)):
        raise FileNotFoundError(f"모델 파일이 누락되었습니다: {model_dir}")

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    if config is None:
        config = MLConfig(
            lookback_days=int(meta["lookback_days"]),
            horizon_days=int(meta["horizon_days"]),
            features=list(meta["features"]),
            up_threshold=float(meta.get("up_threshold", 0.01)),
            down_threshold=float(meta.get("down_threshold", -0.01)),
            hidden_size=int(meta.get("hidden_size", 64)),
            num_layers=int(meta.get("num_layers", 2)),
            dropout=float(meta.get("dropout", 0.2)),
            stock_code=str(meta.get("stock_code", "")),
        )

    model = build_model(config)
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()

    scaler = joblib.load(scaler_path)
    return model, scaler, meta


def predict_from_ohlcv(
    ohlcv: pd.DataFrame,
    config: MLConfig,
    model_dir: str | None = None,
) -> PredictionResult:
    """OHLCV → 추론 결과.

    가장 최근 lookback_days 시퀀스만 사용한다.

    Args:
        ohlcv: 최소 (lookback_days + 워밍업 여유) 길이의 시계열
        config: MLConfig (stock_code, horizon_days 필수)
        model_dir: 명시 디렉토리 (None 이면 config.model_path() 사용)

    Returns:
        PredictionResult
    """
    torch = _import_torch()

    save_dir = model_dir or config.model_path()
    model, scaler, _meta = load_model(save_dir, config)

    # 피처 생성 → 최근 lookback 행 추출
    feat_df = build_features(ohlcv, config.features)
    if len(feat_df) < config.lookback_days:
        raise ValueError(
            f"추론에 필요한 피처 행 수가 부족합니다: "
            f"필요={config.lookback_days}, 제공={len(feat_df)}"
        )

    window = feat_df.iloc[-config.lookback_days :].to_numpy(dtype=np.float32)  # (lookback, n_features)
    window_scaled = apply_scaler(window[np.newaxis, ...], scaler)  # (1, lookback, n_features)

    with torch.no_grad():
        x = torch.from_numpy(window_scaled).float()
        logits = model(x)  # (1, 3)
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

    pred_idx = int(np.argmax(probs))
    asof = _last_index_date(ohlcv)

    return PredictionResult(
        direction=DIRECTION_LABELS[pred_idx],
        confidence=float(probs[pred_idx]),
        prob_down=float(probs[0]),
        prob_flat=float(probs[1]),
        prob_up=float(probs[2]),
        model_key=config.model_key,
        asof_date=asof,
        horizon_days=config.horizon_days,
    )


def predictions_to_ml_record(
    result: PredictionResult,
    last_close: float,
) -> dict[str, Any]:
    """`tp_analysis.ml_predictions` 행을 만들기 위한 dict 변환.

    기존 DDL 스키마는 (pred_mean, pred_lower, pred_upper) 형태로 회귀 결과 저장을 가정한다.
    분류 결과를 다음과 같이 매핑한다:
        pred_mean  = last_close * (1 + expected_return_class_midpoint)
        pred_lower = last_close * (1 - 변동 폭)
        pred_upper = last_close * (1 + 변동 폭)
        confidence(=prob) 와 direction 은 model_version 문자열로 인코딩

    `model_version` 포맷: "lstm-v1-{direction}-{conf%}"
        예: "lstm-v1-UP-72" (UP 클래스 72% 확률)
    """
    # 클래스 중간값: DOWN=-2%, FLAT=0%, UP=+2%
    midpoints = {"DOWN": -0.02, "FLAT": 0.0, "UP": 0.02}
    bands = {"DOWN": 0.015, "FLAT": 0.01, "UP": 0.015}

    mid_ret = midpoints[result.direction]
    band = bands[result.direction]

    pred_mean = last_close * (1.0 + mid_ret)
    pred_lower = last_close * (1.0 + mid_ret - band)
    pred_upper = last_close * (1.0 + mid_ret + band)

    version = f"lstm-v1-{result.direction}-{int(round(result.confidence * 100))}"

    return {
        "base_date": result.asof_date,
        "horizon": result.horizon_days,
        "pred_mean": Decimal(f"{pred_mean:.4f}"),
        "pred_lower": Decimal(f"{pred_lower:.4f}"),
        "pred_upper": Decimal(f"{pred_upper:.4f}"),
        "model_version": version,
        # 직관적 분류 메트릭 매핑
        # mape: 미정 → None
        # direction_acc: 클래스 확률을 0~1 그대로 저장
        "mape": None,
        "direction_acc": Decimal(f"{result.confidence:.4f}"),
    }


def _last_index_date(df: pd.DataFrame) -> date:
    """DataFrame 의 마지막 인덱스를 date 로 변환."""
    idx = df.index[-1]
    if isinstance(idx, datetime):
        return idx.date()
    if isinstance(idx, pd.Timestamp):
        return idx.date()
    if isinstance(idx, date):
        return idx
    return date.today()
