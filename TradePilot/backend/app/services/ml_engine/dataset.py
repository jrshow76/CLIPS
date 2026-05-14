"""PyTorch Dataset / DataLoader (lazy import).

학습 파이프라인의 입력 단계.

핵심 책임:
1. OHLCV 시계열 → 피처 변환 (features.build_features)
2. 시간 분할 train/val (시계열 누수 방지 - 인덱스 기반 분할)
3. StandardScaler 는 train 데이터로만 fit, val 에는 transform 만 적용
4. 윈도잉: t-lookback ... t-1 입력 / t+horizon 라벨
5. PyTorch Dataset 으로 래핑

torch 미설치 환경에서도 import 단계는 통과하도록 lazy import.

ruff 비활성: 본 모듈은 머신러닝 관습 변수명(X, y) 을 사용한다.
"""
# ruff: noqa: N803, N806
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.services.ml_engine.config import MLConfig
from app.services.ml_engine.features import (
    build_features,
    class_weights,
    label_horizon_class,
)


def _import_torch():
    """torch lazy import. 미설치 시 명확한 메시지로 ImportError."""
    try:
        import torch
        from torch.utils.data import DataLoader, Dataset
        return torch, Dataset, DataLoader
    except ImportError as e:  # pragma: no cover - torch 미설치 환경
        raise ImportError(
            "PyTorch 가 설치되어 있지 않습니다. "
            "`pip install torch>=2.2` 또는 backend/pyproject.toml 의 ml extras 를 설치하세요."
        ) from e


@dataclass
class WindowedArrays:
    """윈도잉 결과 numpy 배열 묶음."""

    X: np.ndarray   # shape: (N, lookback, n_features)
    y: np.ndarray   # shape: (N,)  값: 0/1/2

    def __len__(self) -> int:
        return len(self.X)


def make_windows(
    features_df: pd.DataFrame,
    labels: pd.Series,
    lookback: int,
) -> WindowedArrays:
    """sliding window 로 (X, y) 산출.

    Args:
        features_df: 피처 DataFrame (이미 dropna 완료)
        labels: 동일 인덱스의 라벨 시리즈 (-1 = 미래 부족)
        lookback: 입력 시퀀스 길이

    Returns:
        WindowedArrays
    """
    # 피처/라벨 인덱스 정렬 (교집합)
    common_idx = features_df.index.intersection(labels.index)
    if len(common_idx) <= lookback:
        return WindowedArrays(X=np.zeros((0, lookback, features_df.shape[1])), y=np.zeros(0))

    feat = features_df.loc[common_idx].to_numpy(dtype=np.float32)
    y_full = labels.loc[common_idx].to_numpy(dtype=np.int64)

    xs: list[np.ndarray] = []
    ys: list[int] = []
    for t in range(lookback, len(common_idx)):
        if y_full[t] < 0:
            continue  # 미래 부족
        window = feat[t - lookback : t]  # (lookback, n_features)
        xs.append(window)
        ys.append(int(y_full[t]))

    if not xs:
        return WindowedArrays(X=np.zeros((0, lookback, features_df.shape[1])), y=np.zeros(0))

    X = np.stack(xs, axis=0).astype(np.float32)
    y = np.asarray(ys, dtype=np.int64)
    return WindowedArrays(X=X, y=y)


def time_split(arr: WindowedArrays, val_split: float) -> tuple[WindowedArrays, WindowedArrays]:
    """시계열 분할 (앞 train / 뒤 val).

    랜덤 셔플을 사용하지 않는다 (look-ahead 방지).
    """
    n = len(arr)
    if n == 0:
        return arr, arr
    n_val = max(1, int(n * val_split))
    n_train = n - n_val
    train = WindowedArrays(X=arr.X[:n_train], y=arr.y[:n_train])
    val = WindowedArrays(X=arr.X[n_train:], y=arr.y[n_train:])
    return train, val


def fit_scaler(X: np.ndarray) -> Any:
    """StandardScaler 를 (N*lookback, n_features) 형태로 fit.

    sklearn import 도 lazy 처리.
    """
    from sklearn.preprocessing import StandardScaler

    if X.size == 0:
        scaler = StandardScaler()
        # 빈 데이터에 대해서도 transform 동작하도록 placeholder fit
        scaler.mean_ = np.zeros(1, dtype=np.float32)
        scaler.scale_ = np.ones(1, dtype=np.float32)
        scaler.var_ = np.ones(1, dtype=np.float32)
        scaler.n_features_in_ = 1
        return scaler
    flat = X.reshape(-1, X.shape[-1])
    scaler = StandardScaler()
    scaler.fit(flat)
    return scaler


def apply_scaler(X: np.ndarray, scaler: Any) -> np.ndarray:
    """학습된 scaler 로 transform (3D 유지)."""
    if X.size == 0:
        return X
    shape = X.shape
    flat = X.reshape(-1, shape[-1])
    out = scaler.transform(flat).astype(np.float32)
    return out.reshape(shape)


class StockSequenceDataset:
    """PyTorch Dataset 어댑터. lazy 하게 torch 를 import 한다.

    instance 가 처음 인덱싱될 때 torch 가 로드되며, 그 전에는 numpy 만 사용.
    """

    def __init__(self, X: np.ndarray, y: np.ndarray) -> None:
        self.X = X
        self.y = y

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        torch, _Dataset, _DataLoader = _import_torch()
        x = torch.from_numpy(self.X[idx]).float()
        y = torch.tensor(self.y[idx], dtype=torch.long)
        return x, y


class MultiStockSequenceDataset:
    """다중 종목 윈도우 묶음 Dataset.

    각 샘플은 (X, y, stock_id) 형태로 제공된다.
    글로벌 모델 학습용. sample_weight 도 선택적으로 부착할 수 있다.
    """

    def __init__(
        self,
        X: np.ndarray,
        y: np.ndarray,
        stock_ids: np.ndarray,
        sample_weights: np.ndarray | None = None,
    ) -> None:
        if not (len(X) == len(y) == len(stock_ids)):
            raise ValueError("X/y/stock_ids 길이가 일치해야 합니다")
        if sample_weights is not None and len(sample_weights) != len(X):
            raise ValueError("sample_weights 길이가 X 와 일치해야 합니다")
        self.X = X
        self.y = y
        self.stock_ids = stock_ids.astype(np.int64)
        self.sample_weights = (
            sample_weights.astype(np.float32) if sample_weights is not None else None
        )

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        torch, _Dataset, _DataLoader = _import_torch()
        x = torch.from_numpy(self.X[idx]).float()
        y = torch.tensor(self.y[idx], dtype=torch.long)
        sid = torch.tensor(self.stock_ids[idx], dtype=torch.long)
        if self.sample_weights is not None:
            w = torch.tensor(self.sample_weights[idx], dtype=torch.float32)
            return x, y, sid, w
        return x, y, sid


class SectorSequenceDataset:
    """단일 섹터 내 다중 종목 윈도우 묶음 Dataset.

    섹터 모델 학습용. 종목 ID 임베딩은 없으나, 디버그/메타 기록을 위해
    stock_ids 를 보관한다.
    """

    def __init__(
        self,
        X: np.ndarray,
        y: np.ndarray,
        stock_ids: np.ndarray,
        sample_weights: np.ndarray | None = None,
    ) -> None:
        self.X = X
        self.y = y
        self.stock_ids = stock_ids.astype(np.int64)
        self.sample_weights = (
            sample_weights.astype(np.float32) if sample_weights is not None else None
        )

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        torch, _Dataset, _DataLoader = _import_torch()
        x = torch.from_numpy(self.X[idx]).float()
        y = torch.tensor(self.y[idx], dtype=torch.long)
        # 섹터 모델은 stock_id 를 사용하지 않지만, 인터페이스 일관성을 위해 반환
        sid = torch.tensor(self.stock_ids[idx], dtype=torch.long)
        if self.sample_weights is not None:
            w = torch.tensor(self.sample_weights[idx], dtype=torch.float32)
            return x, y, sid, w
        return x, y, sid


def build_dataset_from_ohlcv(
    df: pd.DataFrame,
    config: MLConfig,
) -> tuple[WindowedArrays, WindowedArrays, Any, dict[str, Any]]:
    """OHLCV → (train_arr, val_arr, scaler, meta) 풀 파이프라인.

    학습 진입점에서 호출되는 통합 함수.

    Returns:
        train_arr: 학습용 (scaler 적용 완료)
        val_arr:   검증용 (scaler transform 만 적용)
        scaler:    학습 데이터로 fit 된 StandardScaler
        meta:      라벨 분포, 클래스 가중치, 행 수 등 메타데이터
    """
    # 1) 피처
    features_df = build_features(df, config.features)
    # 2) 라벨
    labels = label_horizon_class(
        df["close"].reindex(features_df.index),
        horizon_days=config.horizon_days,
        up_threshold=config.up_threshold,
        down_threshold=config.down_threshold,
    )
    # 3) 윈도잉
    arr = make_windows(features_df, labels, lookback=config.lookback_days)
    # 4) 시간 분할
    train_raw, val_raw = time_split(arr, val_split=config.val_split)
    # 5) 스케일러 fit (train 만)
    scaler = fit_scaler(train_raw.X)
    train = WindowedArrays(X=apply_scaler(train_raw.X, scaler), y=train_raw.y)
    val = WindowedArrays(X=apply_scaler(val_raw.X, scaler), y=val_raw.y)
    # 6) 메타 (클래스 분포)
    weights = class_weights(arr.y, num_classes=config.num_classes)
    label_dist = {
        int(c): int((arr.y == c).sum()) for c in range(config.num_classes)
    }
    meta = {
        "n_samples": int(len(arr)),
        "n_train": int(len(train)),
        "n_val": int(len(val)),
        "label_dist": label_dist,
        "class_weights": [float(w) for w in weights],
        "features": list(config.features),
        "lookback": config.lookback_days,
        "horizon": config.horizon_days,
    }
    return train, val, scaler, meta


def make_loaders(
    train_arr: WindowedArrays,
    val_arr: WindowedArrays,
    batch_size: int,
) -> tuple[Any, Any]:
    """PyTorch DataLoader 생성. torch lazy import."""
    _torch, _Dataset, DataLoader = _import_torch()

    # 간단한 어댑터: StockSequenceDataset 은 __getitem__ 에서 tensor 변환
    train_ds = StockSequenceDataset(train_arr.X, train_arr.y)
    val_ds = StockSequenceDataset(val_arr.X, val_arr.y)
    # CPU 환경 가정: num_workers=0 (멀티프로세스 비용 회피)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    return train_loader, val_loader
