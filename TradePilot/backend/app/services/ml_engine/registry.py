"""모델 메타 레지스트리.

`ML_MODEL_DIR` 하위의 디렉토리들을 모델 카탈로그로 노출한다.
DB 테이블에는 *예측 결과*만 저장하고, 학습된 모델 파일 자체는 파일시스템 기반으로 관리한다.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class ModelMeta:
    """모델 메타데이터."""

    model_key: str           # 예: "005930_3d"
    stock_code: str
    horizon_days: int
    lookback_days: int
    features: list[str]
    best_val_loss: float | None
    best_val_acc: float | None
    best_val_f1: float | None
    trained_at: str | None
    model_param_count: int | None
    model_path: str          # 파일 디렉토리 절대 경로

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_key": self.model_key,
            "stock_code": self.stock_code,
            "horizon_days": self.horizon_days,
            "lookback_days": self.lookback_days,
            "features": self.features,
            "best_val_loss": self.best_val_loss,
            "best_val_acc": self.best_val_acc,
            "best_val_f1": self.best_val_f1,
            "trained_at": self.trained_at,
            "model_param_count": self.model_param_count,
            "model_path": self.model_path,
        }


def get_model_dir(base: str | None = None) -> str:
    """모델 디렉토리 베이스 경로 (환경변수 우선)."""
    if base:
        return base
    env = os.getenv("ML_MODEL_DIR")
    if env:
        return env
    return settings.ML_MODEL_DIR


def list_models(base: str | None = None) -> list[ModelMeta]:
    """등록된 모델 메타 목록."""
    root = get_model_dir(base)
    if not os.path.isdir(root):
        return []
    out: list[ModelMeta] = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isdir(path):
            continue
        meta_path = os.path.join(path, "meta.json")
        if not os.path.exists(meta_path):
            continue
        meta = _load_meta(meta_path, path, name)
        if meta is not None:
            out.append(meta)
    return out


def get_model_meta(model_key: str, base: str | None = None) -> ModelMeta | None:
    """특정 모델 메타 조회."""
    root = get_model_dir(base)
    path = os.path.join(root, model_key)
    meta_path = os.path.join(path, "meta.json")
    if not os.path.exists(meta_path):
        return None
    return _load_meta(meta_path, path, model_key)


def model_exists(stock_code: str, horizon_days: int, base: str | None = None) -> bool:
    """학습된 모델 파일이 존재하는지 확인."""
    root = get_model_dir(base)
    key = f"{stock_code}_{horizon_days}d"
    return os.path.exists(os.path.join(root, key, "model.pt"))


def _load_meta(meta_path: str, dir_path: str, model_key: str) -> ModelMeta | None:
    try:
        with open(meta_path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    return ModelMeta(
        model_key=model_key,
        stock_code=raw.get("stock_code", ""),
        horizon_days=int(raw.get("horizon_days", 0)),
        lookback_days=int(raw.get("lookback_days", 0)),
        features=list(raw.get("features", [])),
        best_val_loss=_safe_float(raw.get("best_val_loss")),
        best_val_acc=_safe_float(raw.get("best_val_acc")),
        best_val_f1=_safe_float(raw.get("best_val_f1")),
        trained_at=raw.get("trained_at"),
        model_param_count=raw.get("model_param_count"),
        model_path=dir_path,
    )


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
