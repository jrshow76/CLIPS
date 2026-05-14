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
from app.services.ml_engine.model import (
    build_model,
    build_multistock_model,
    build_sector_model,
)
from app.services.ml_engine.registry import (
    ModelKind,
    get_model_for_stock,
    get_model_meta,
)

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


# ============================================================================
# 멀티 종목 모델 로드 / 추론
# ============================================================================
def load_multi_model(model_dir: str) -> tuple[Any, Any, dict[str, Any]]:
    """저장된 섹터/글로벌 모델 로드.

    meta.json 의 model_kind 와 num_stocks 를 사용해 적절한 모델 클래스를 생성.

    Returns:
        (model, scaler, meta)
    """
    torch = _import_torch()
    import joblib

    meta_path = os.path.join(model_dir, "meta.json")
    state_path = os.path.join(model_dir, "model.pt")
    scaler_path = os.path.join(model_dir, "scaler.joblib")

    if not (os.path.exists(meta_path) and os.path.exists(state_path) and os.path.exists(scaler_path)):
        raise FileNotFoundError(f"멀티 모델 파일이 누락되었습니다: {model_dir}")

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    config = MLConfig(
        lookback_days=int(meta["lookback_days"]),
        horizon_days=int(meta["horizon_days"]),
        features=list(meta["features"]),
        up_threshold=float(meta.get("up_threshold", 0.01)),
        down_threshold=float(meta.get("down_threshold", -0.01)),
        hidden_size=int(meta.get("hidden_size", 64)),
        num_layers=int(meta.get("num_layers", 2)),
        dropout=float(meta.get("dropout", 0.2)),
    )

    kind = meta.get("model_kind", "INDIVIDUAL")
    if kind == "SECTOR":
        model = build_sector_model(config)
    elif kind == "GLOBAL":
        num_stocks = int(meta.get("num_stocks", 1))
        embed_dim = int(meta.get("embed_dim", 8))
        model = build_multistock_model(config, num_stocks=num_stocks, embed_dim=embed_dim)
    else:
        model = build_model(config)

    state = torch.load(state_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()

    scaler = joblib.load(scaler_path)
    return model, scaler, meta


def predict_with_model(
    ohlcv: pd.DataFrame,
    model: Any,
    scaler: Any,
    meta: dict[str, Any],
    stock_code: str | None = None,
) -> PredictionResult:
    """이미 로드한 (model, scaler, meta) 로 단건 추론.

    meta.model_kind 에 따라 individual/sector/global 분기 처리.
    """
    torch = _import_torch()
    import numpy as np_ml

    kind = meta.get("model_kind", "INDIVIDUAL")
    lookback = int(meta.get("lookback_days", 60))
    features = list(meta.get("features", []))
    horizon_days = int(meta.get("horizon_days", 1))

    feat_df = build_features(ohlcv, features)
    if len(feat_df) < lookback:
        raise ValueError(
            f"추론에 필요한 피처 행 수가 부족합니다: 필요={lookback}, 제공={len(feat_df)}"
        )

    window = feat_df.iloc[-lookback:].to_numpy(dtype=np_ml.float32)
    window_scaled = apply_scaler(window[np_ml.newaxis, ...], scaler)

    with torch.no_grad():
        x = torch.from_numpy(window_scaled).float()
        if kind == "GLOBAL":
            stock_to_id = meta.get("stock_to_id", {}) or {}
            sid = int(stock_to_id.get(stock_code or "", -1))
            if sid < 0:
                # 미등록 종목 → 임베딩 평균을 위해 임의 인덱스 0 사용 (warm start)
                # 추후 신규 종목 처리 정책으로 개선 가능
                sid = 0
                log.warning(
                    "ml_global_predict_unknown_stock",
                    stock_code=stock_code,
                    fallback_sid=sid,
                )
            sid_t = torch.tensor([sid], dtype=torch.long)
            logits = model(x, sid_t)
        elif kind == "SECTOR":
            logits = model(x)
        else:
            logits = model(x)
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

    pred_idx = int(np_ml.argmax(probs))
    asof = _last_index_date(ohlcv)

    # 모델 키 추출 (디렉토리명 == 키)
    model_key = meta.get("model_key") or _model_key_from_meta(meta, stock_code)
    return PredictionResult(
        direction=DIRECTION_LABELS[pred_idx],
        confidence=float(probs[pred_idx]),
        prob_down=float(probs[0]),
        prob_flat=float(probs[1]),
        prob_up=float(probs[2]),
        model_key=model_key,
        asof_date=asof,
        horizon_days=horizon_days,
    )


def _model_key_from_meta(meta: dict[str, Any], stock_code: str | None) -> str:
    kind = meta.get("model_kind", "INDIVIDUAL")
    horizon = int(meta.get("horizon_days", 1))
    if kind == "SECTOR":
        return f"sector_{meta.get('identifier', '')}_{horizon}d"
    if kind == "GLOBAL":
        return f"global_{horizon}d"
    return f"{stock_code or meta.get('stock_code', 'unknown')}_{horizon}d"


# ============================================================================
# 앙상블 추론
# ============================================================================
def _predict_individual_probs(
    ohlcv: pd.DataFrame, stock_code: str, horizon: int, base: str | None = None
) -> tuple[Any, str] | None:
    """개별 모델 추론 → (probs, model_key) 또는 None.

    probs: ndarray shape (3,) - [down, flat, up]
    """
    meta = get_model_meta(f"{stock_code}_{horizon}d", base=base)
    if meta is None:
        return None
    try:
        # load_model 에 config=None 을 전달하여 meta.json 으로부터 구성
        model, scaler, raw_meta = load_model(meta.model_path, config=None)
        torch = _import_torch()
        import numpy as np_ml

        feat_df = build_features(ohlcv, list(raw_meta.get("features", [])))
        lookback = int(raw_meta.get("lookback_days", 60))
        if len(feat_df) < lookback:
            return None
        window = feat_df.iloc[-lookback:].to_numpy(dtype=np_ml.float32)
        window_scaled = apply_scaler(window[np_ml.newaxis, ...], scaler)
        with torch.no_grad():
            x = torch.from_numpy(window_scaled).float()
            logits = model(x)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
        return probs, meta.model_key
    except Exception as e:  # pragma: no cover
        log.warning("ml_predict_individual_failed", stock_code=stock_code, error=str(e))
        return None


def _predict_sector_probs(
    ohlcv: pd.DataFrame,
    stock_code: str,
    sector_code: str,
    horizon: int,
    base: str | None = None,
) -> tuple[Any, str] | None:
    meta = get_model_meta(f"sector_{sector_code}_{horizon}d", base=base)
    if meta is None:
        return None
    try:
        model, scaler, raw_meta = load_multi_model(meta.model_path)
        result = predict_with_model(ohlcv, model, scaler, raw_meta, stock_code=stock_code)
        import numpy as np_ml

        probs = np_ml.array([result.prob_down, result.prob_flat, result.prob_up])
        return probs, meta.model_key
    except Exception as e:  # pragma: no cover
        log.warning("ml_predict_sector_failed", stock_code=stock_code, error=str(e))
        return None


def _predict_global_probs(
    ohlcv: pd.DataFrame,
    stock_code: str,
    horizon: int,
    base: str | None = None,
) -> tuple[Any, str] | None:
    meta = get_model_meta(f"global_{horizon}d", base=base)
    if meta is None:
        return None
    try:
        model, scaler, raw_meta = load_multi_model(meta.model_path)
        result = predict_with_model(ohlcv, model, scaler, raw_meta, stock_code=stock_code)
        import numpy as np_ml

        probs = np_ml.array([result.prob_down, result.prob_flat, result.prob_up])
        return probs, meta.model_key
    except Exception as e:  # pragma: no cover
        log.warning("ml_predict_global_failed", stock_code=stock_code, error=str(e))
        return None


# 기본 가중치
DEFAULT_ENSEMBLE_WEIGHTS_FULL = {"INDIVIDUAL": 0.5, "SECTOR": 0.3, "GLOBAL": 0.2}
DEFAULT_ENSEMBLE_WEIGHTS_NO_INDIVIDUAL = {"SECTOR": 0.6, "GLOBAL": 0.4}


@dataclass
class EnsembleResult:
    """앙상블 추론 결과."""

    direction: str
    confidence: float
    prob_down: float
    prob_flat: float
    prob_up: float
    horizon_days: int
    asof_date: date
    contributions: dict[str, dict[str, Any]]  # 모델별 기여 (probs, weight, model_key)
    used_kinds: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "prob_down": self.prob_down,
            "prob_flat": self.prob_flat,
            "prob_up": self.prob_up,
            "horizon_days": self.horizon_days,
            "asof_date": self.asof_date.isoformat(),
            "contributions": self.contributions,
            "used_kinds": self.used_kinds,
        }


def predict_ensemble(
    ohlcv: pd.DataFrame,
    stock_code: str,
    horizon: int = 1,
    *,
    sector_code: str | None = None,
    models: list[str] | None = None,
    weights: dict[str, float] | None = None,
    base: str | None = None,
) -> EnsembleResult:
    """가중 평균 앙상블 추론.

    Args:
        ohlcv: 최근 시계열 (충분한 워밍업)
        stock_code: 종목 코드
        horizon: 예측 호라이즌
        sector_code: 섹터 코드 (SECTOR 모델 선택용). None 이면 SECTOR 사용 안함.
        models: 사용 모델 종류 리스트 (기본 ["INDIVIDUAL","SECTOR","GLOBAL"])
        weights: 가중치 dict. None 이면 기본 가중치 사용.
                 개별 모델이 없으면 자동으로 (SECTOR:0.6, GLOBAL:0.4) 로 재정규화.

    Returns:
        EnsembleResult
    """
    import numpy as np_ml

    requested = models or ["INDIVIDUAL", "SECTOR", "GLOBAL"]
    contributions: dict[str, dict[str, Any]] = {}

    # 각 모델 추론
    individual_out: tuple[Any, str] | None = None
    sector_out: tuple[Any, str] | None = None
    global_out: tuple[Any, str] | None = None

    if "INDIVIDUAL" in requested:
        individual_out = _predict_individual_probs(ohlcv, stock_code, horizon, base=base)
    if "SECTOR" in requested and sector_code:
        sector_out = _predict_sector_probs(ohlcv, stock_code, sector_code, horizon, base=base)
    if "GLOBAL" in requested:
        global_out = _predict_global_probs(ohlcv, stock_code, horizon, base=base)

    # 가중치 정규화
    used_weights = dict(weights) if weights else dict(DEFAULT_ENSEMBLE_WEIGHTS_FULL)
    has_individual = individual_out is not None
    has_sector = sector_out is not None
    has_global = global_out is not None

    if not (has_individual or has_sector or has_global):
        raise FileNotFoundError(
            f"앙상블 가능한 모델이 없습니다: stock={stock_code}, horizon={horizon}"
        )

    # 개별 모델이 없으면 SECTOR/GLOBAL 만 사용 → 가중치 재조정
    if not has_individual and weights is None:
        used_weights = dict(DEFAULT_ENSEMBLE_WEIGHTS_NO_INDIVIDUAL)

    # 누락 모델 가중치 제거 후 정규화
    active_kinds: list[str] = []
    if has_individual:
        active_kinds.append("INDIVIDUAL")
    if has_sector:
        active_kinds.append("SECTOR")
    if has_global:
        active_kinds.append("GLOBAL")

    active_weights = {k: used_weights.get(k, 0.0) for k in active_kinds}
    total_w = sum(active_weights.values())
    if total_w <= 0:
        # 모든 가중치 0 → 균등 분배
        active_weights = {k: 1.0 / len(active_kinds) for k in active_kinds}
        total_w = 1.0
    norm_weights = {k: w / total_w for k, w in active_weights.items()}

    # 가중 평균
    combined = np_ml.zeros(3, dtype=np_ml.float32)
    for kind, out in (
        ("INDIVIDUAL", individual_out),
        ("SECTOR", sector_out),
        ("GLOBAL", global_out),
    ):
        if out is None:
            continue
        probs, mkey = out
        w = norm_weights[kind]
        combined += probs.astype(np_ml.float32) * w
        contributions[kind] = {
            "model_key": mkey,
            "prob_down": float(probs[0]),
            "prob_flat": float(probs[1]),
            "prob_up": float(probs[2]),
            "weight": float(w),
        }

    # 정규화 (수치 오차 보정)
    s = float(combined.sum())
    if s > 0:
        combined = combined / s

    pred_idx = int(np_ml.argmax(combined))
    asof = _last_index_date(ohlcv)
    return EnsembleResult(
        direction=DIRECTION_LABELS[pred_idx],
        confidence=float(combined[pred_idx]),
        prob_down=float(combined[0]),
        prob_flat=float(combined[1]),
        prob_up=float(combined[2]),
        horizon_days=horizon,
        asof_date=asof,
        contributions=contributions,
        used_kinds=active_kinds,
    )


def predict_auto(
    ohlcv: pd.DataFrame,
    stock_code: str,
    horizon: int = 1,
    *,
    sector_code: str | None = None,
    base: str | None = None,
) -> PredictionResult:
    """모델 자동 선택 추론 (단일 모델, 앙상블 없음).

    registry.get_model_for_stock 결과로 가장 적합한 모델을 선택해 추론한다.
    """
    meta = get_model_for_stock(
        stock_code, horizon, sector_code=sector_code, base=base
    )
    if meta is None:
        raise FileNotFoundError(
            f"사용 가능한 모델이 없습니다: stock={stock_code}, horizon={horizon}"
        )

    if meta.kind == ModelKind.INDIVIDUAL:
        config = MLConfig(stock_code=stock_code, horizon_days=horizon)
        return predict_from_ohlcv(ohlcv, config, model_dir=meta.model_path)

    # SECTOR / GLOBAL
    model, scaler, raw_meta = load_multi_model(meta.model_path)
    raw_meta.setdefault("model_key", meta.model_key)
    return predict_with_model(ohlcv, model, scaler, raw_meta, stock_code=stock_code)
