"""모델 메타 레지스트리.

`ML_MODEL_DIR` 하위의 디렉토리들을 모델 카탈로그로 노출한다.
DB 테이블에는 *예측 결과*만 저장하고, 학습된 모델 파일 자체는 파일시스템 기반으로 관리한다.

모델 종류:
    - INDIVIDUAL : 종목별 단일 모델   (key 예: "005930_3d")
    - SECTOR     : 섹터 공통 모델     (key 예: "sector_SEMI_3d")
    - GLOBAL     : 전 종목 글로벌 모델 (key 예: "global_3d")
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from app.core.config import settings


class ModelKind(str, Enum):
    """모델 종류."""

    INDIVIDUAL = "INDIVIDUAL"
    SECTOR = "SECTOR"
    GLOBAL = "GLOBAL"


# 종목별 모델이 "신선하다" 고 판단할 최대 일수
FRESH_INDIVIDUAL_DAYS = 7


@dataclass
class ModelMeta:
    """모델 메타데이터."""

    model_key: str           # 예: "005930_3d", "sector_SEMI_3d", "global_3d"
    kind: ModelKind          # 모델 종류
    horizon_days: int
    lookback_days: int
    features: list[str]
    best_val_loss: float | None
    best_val_acc: float | None
    best_val_f1: float | None
    trained_at: str | None
    model_param_count: int | None
    model_path: str          # 파일 디렉토리 절대 경로
    # 종류별 부가 필드
    stock_code: str = ""              # INDIVIDUAL 전용
    identifier: str = ""              # SECTOR(섹터코드) / GLOBAL("global")
    num_stocks: int = 1               # SECTOR/GLOBAL: 학습 대상 종목 수
    stock_to_id: dict[str, int] = field(default_factory=dict)  # GLOBAL 임베딩 인덱스

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_key": self.model_key,
            "kind": self.kind.value,
            "stock_code": self.stock_code,
            "identifier": self.identifier,
            "horizon_days": self.horizon_days,
            "lookback_days": self.lookback_days,
            "features": self.features,
            "best_val_loss": self.best_val_loss,
            "best_val_acc": self.best_val_acc,
            "best_val_f1": self.best_val_f1,
            "trained_at": self.trained_at,
            "model_param_count": self.model_param_count,
            "model_path": self.model_path,
            "num_stocks": self.num_stocks,
        }

    def is_fresh(self, max_days: int = FRESH_INDIVIDUAL_DAYS) -> bool:
        """학습일이 max_days 이내인지."""
        if not self.trained_at:
            return False
        try:
            ts = datetime.fromisoformat(self.trained_at.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            return (datetime.now(UTC) - ts) < timedelta(days=max_days)
        except (ValueError, TypeError):
            return False


def get_model_dir(base: str | None = None) -> str:
    """모델 디렉토리 베이스 경로 (환경변수 우선)."""
    if base:
        return base
    env = os.getenv("ML_MODEL_DIR")
    if env:
        return env
    return settings.ML_MODEL_DIR


def list_models(base: str | None = None) -> list[ModelMeta]:
    """등록된 모델 메타 목록 (모든 종류)."""
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


def list_available_models(base: str | None = None) -> dict[str, list[dict[str, Any]]]:
    """모든 모델 메타데이터를 종류별로 분리하여 조회."""
    models = list_models(base)
    grouped: dict[str, list[dict[str, Any]]] = {
        ModelKind.INDIVIDUAL.value: [],
        ModelKind.SECTOR.value: [],
        ModelKind.GLOBAL.value: [],
    }
    for m in models:
        grouped[m.kind.value].append(m.to_dict())
    return grouped


def get_model_meta(model_key: str, base: str | None = None) -> ModelMeta | None:
    """특정 모델 메타 조회."""
    root = get_model_dir(base)
    path = os.path.join(root, model_key)
    meta_path = os.path.join(path, "meta.json")
    if not os.path.exists(meta_path):
        return None
    return _load_meta(meta_path, path, model_key)


def model_exists(stock_code: str, horizon_days: int, base: str | None = None) -> bool:
    """학습된 종목별 모델 파일이 존재하는지 확인 (INDIVIDUAL)."""
    root = get_model_dir(base)
    key = f"{stock_code}_{horizon_days}d"
    return os.path.exists(os.path.join(root, key, "model.pt"))


def sector_model_exists(sector_code: str, horizon_days: int, base: str | None = None) -> bool:
    """학습된 섹터 모델이 존재하는지."""
    root = get_model_dir(base)
    key = f"sector_{sector_code}_{horizon_days}d"
    return os.path.exists(os.path.join(root, key, "model.pt"))


def global_model_exists(horizon_days: int, base: str | None = None) -> bool:
    """학습된 글로벌 모델이 존재하는지."""
    root = get_model_dir(base)
    key = f"global_{horizon_days}d"
    return os.path.exists(os.path.join(root, key, "model.pt"))


def get_model_for_stock(
    stock_code: str,
    horizon_days: int,
    *,
    sector_code: str | None = None,
    base: str | None = None,
    fresh_days: int = FRESH_INDIVIDUAL_DAYS,
) -> ModelMeta | None:
    """추론용 모델 선택 (우선순위: 개별 → 섹터 → 글로벌).

    선택 우선순위:
        1) 종목별 모델이 있고 fresh_days 이내 학습 → INDIVIDUAL
        2) 섹터 모델이 있으면 → SECTOR
        3) 글로벌 모델이 있으면 → GLOBAL
        4) None
    """
    base_dir = get_model_dir(base)

    # 1) 개별 모델
    individual_key = f"{stock_code}_{horizon_days}d"
    individual_meta = get_model_meta(individual_key, base=base_dir)
    if individual_meta is not None and individual_meta.is_fresh(max_days=fresh_days):
        return individual_meta

    # 2) 섹터 모델
    if sector_code:
        sector_key = f"sector_{sector_code}_{horizon_days}d"
        sector_meta = get_model_meta(sector_key, base=base_dir)
        if sector_meta is not None:
            return sector_meta

    # 3) 글로벌 모델
    global_key = f"global_{horizon_days}d"
    global_meta = get_model_meta(global_key, base=base_dir)
    if global_meta is not None:
        return global_meta

    # 4) 개별 모델이 stale 이라도 있으면 fallback 으로 반환
    if individual_meta is not None:
        return individual_meta

    return None


def _detect_kind(meta_raw: dict[str, Any], model_key: str) -> ModelKind:
    """meta.json + 키 패턴으로 모델 종류 식별."""
    explicit = meta_raw.get("model_kind")
    if explicit == "SECTOR":
        return ModelKind.SECTOR
    if explicit == "GLOBAL":
        return ModelKind.GLOBAL
    if explicit == "INDIVIDUAL":
        return ModelKind.INDIVIDUAL
    # 키 prefix 기반
    if model_key.startswith("sector_"):
        return ModelKind.SECTOR
    if model_key.startswith("global_"):
        return ModelKind.GLOBAL
    return ModelKind.INDIVIDUAL


def _load_meta(meta_path: str, dir_path: str, model_key: str) -> ModelMeta | None:
    try:
        with open(meta_path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    kind = _detect_kind(raw, model_key)
    return ModelMeta(
        model_key=model_key,
        kind=kind,
        stock_code=raw.get("stock_code", ""),
        identifier=raw.get("identifier", ""),
        horizon_days=int(raw.get("horizon_days", 0)),
        lookback_days=int(raw.get("lookback_days", 0)),
        features=list(raw.get("features", [])),
        best_val_loss=_safe_float(raw.get("best_val_loss")),
        best_val_acc=_safe_float(raw.get("best_val_acc")),
        best_val_f1=_safe_float(raw.get("best_val_f1")),
        trained_at=raw.get("trained_at"),
        model_param_count=raw.get("model_param_count"),
        model_path=dir_path,
        num_stocks=int(raw.get("num_stocks", 1)),
        stock_to_id=dict(raw.get("stock_to_id", {})),
    )


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
