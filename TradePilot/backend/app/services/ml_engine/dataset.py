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


# ============================================================================
# 멀티 종목 데이터셋 통합
# ============================================================================
@dataclass
class MultiStockWindowedArrays:
    """다중 종목 윈도우 묶음 (글로벌/섹터 학습용)."""

    X: np.ndarray            # (N, lookback, n_features)
    y: np.ndarray            # (N,)
    stock_ids: np.ndarray    # (N,) - 종목 인덱스 (0..num_stocks-1)
    sample_weights: np.ndarray | None = None  # (N,) - 종목별 가중치

    def __len__(self) -> int:
        return len(self.X)


def build_multistock_dataset_from_ohlcvs(
    ohlcv_by_code: dict[str, pd.DataFrame],
    config: MLConfig,
    *,
    use_sample_weight: bool = True,
) -> tuple[
    MultiStockWindowedArrays,
    MultiStockWindowedArrays,
    Any,
    dict[str, int],
    dict[str, Any],
]:
    """여러 종목 OHLCV → 통합 학습/검증 배열.

    각 종목 내에서 시간 순으로 train/val 을 분할한 뒤, 종목별 split 을 합쳐
    하나의 멀티 종목 배열을 만든다. StandardScaler 는 모든 train 윈도우를
    합친 데이터로 fit 한다.

    Args:
        ohlcv_by_code: {stock_code: OHLCV DataFrame}
        config: MLConfig
        use_sample_weight: 종목별 샘플 수 역수로 가중치 부여 (소수 데이터 보정)

    Returns:
        (train_arr, val_arr, scaler, stock_to_id, meta)
    """
    if not ohlcv_by_code:
        raise ValueError("ohlcv_by_code 가 비어 있습니다")

    # 종목 ID 매핑 (정렬된 코드 기준)
    sorted_codes = sorted(ohlcv_by_code.keys())
    stock_to_id: dict[str, int] = {code: i for i, code in enumerate(sorted_codes)}

    train_X_list: list[np.ndarray] = []
    train_y_list: list[np.ndarray] = []
    train_sid_list: list[np.ndarray] = []
    val_X_list: list[np.ndarray] = []
    val_y_list: list[np.ndarray] = []
    val_sid_list: list[np.ndarray] = []

    per_stock_counts: dict[str, int] = {}

    for code in sorted_codes:
        ohlcv = ohlcv_by_code[code]
        if ohlcv is None or ohlcv.empty:
            per_stock_counts[code] = 0
            continue

        features_df = build_features(ohlcv, config.features)
        labels = label_horizon_class(
            ohlcv["close"].reindex(features_df.index),
            horizon_days=config.horizon_days,
            up_threshold=config.up_threshold,
            down_threshold=config.down_threshold,
        )
        arr = make_windows(features_df, labels, lookback=config.lookback_days)
        if len(arr) == 0:
            per_stock_counts[code] = 0
            continue

        train_raw, val_raw = time_split(arr, val_split=config.val_split)
        sid = stock_to_id[code]

        if len(train_raw) > 0:
            train_X_list.append(train_raw.X)
            train_y_list.append(train_raw.y)
            train_sid_list.append(np.full(len(train_raw), sid, dtype=np.int64))
        if len(val_raw) > 0:
            val_X_list.append(val_raw.X)
            val_y_list.append(val_raw.y)
            val_sid_list.append(np.full(len(val_raw), sid, dtype=np.int64))

        per_stock_counts[code] = len(arr)

    if not train_X_list:
        raise ValueError("학습용 윈도우가 없습니다 (모든 종목이 비어 있음)")

    train_X_all = np.concatenate(train_X_list, axis=0)
    train_y_all = np.concatenate(train_y_list, axis=0)
    train_sid_all = np.concatenate(train_sid_list, axis=0)

    if val_X_list:
        val_X_all = np.concatenate(val_X_list, axis=0)
        val_y_all = np.concatenate(val_y_list, axis=0)
        val_sid_all = np.concatenate(val_sid_list, axis=0)
    else:
        n_feat = train_X_all.shape[-1]
        val_X_all = np.zeros((0, config.lookback_days, n_feat), dtype=np.float32)
        val_y_all = np.zeros(0, dtype=np.int64)
        val_sid_all = np.zeros(0, dtype=np.int64)

    # 스케일러: train 전체에 대해 fit
    scaler = fit_scaler(train_X_all)
    train_X_all = apply_scaler(train_X_all, scaler)
    val_X_all = apply_scaler(val_X_all, scaler)

    # 샘플 가중치 (종목별 샘플 수 역수)
    train_w: np.ndarray | None = None
    if use_sample_weight:
        counts_per_sid = np.bincount(train_sid_all, minlength=len(sorted_codes)).astype(np.float32)
        counts_per_sid = np.where(counts_per_sid == 0, 1.0, counts_per_sid)
        # 정규화: 평균 1.0 이 되도록
        inv = counts_per_sid.mean() / counts_per_sid
        train_w = inv[train_sid_all]

    # 라벨 분포 및 클래스 가중치
    weights = class_weights(np.concatenate([train_y_all, val_y_all]), num_classes=config.num_classes)
    label_dist = {
        int(c): int((train_y_all == c).sum() + (val_y_all == c).sum())
        for c in range(config.num_classes)
    }
    meta = {
        "n_stocks": len(sorted_codes),
        "n_train": int(len(train_X_all)),
        "n_val": int(len(val_X_all)),
        "label_dist": label_dist,
        "class_weights": [float(w) for w in weights],
        "features": list(config.features),
        "lookback": config.lookback_days,
        "horizon": config.horizon_days,
        "per_stock_counts": per_stock_counts,
        "stock_codes": sorted_codes,
    }

    train_arr = MultiStockWindowedArrays(
        X=train_X_all, y=train_y_all, stock_ids=train_sid_all, sample_weights=train_w
    )
    val_arr = MultiStockWindowedArrays(
        X=val_X_all, y=val_y_all, stock_ids=val_sid_all, sample_weights=None
    )
    return train_arr, val_arr, scaler, stock_to_id, meta


def make_multi_loaders(
    train_arr: MultiStockWindowedArrays,
    val_arr: MultiStockWindowedArrays,
    batch_size: int,
    *,
    with_sample_weight: bool = True,
) -> tuple[Any, Any]:
    """멀티 종목 DataLoader 생성.

    train 셔플 / val 비셔플. CPU 환경 num_workers=0.
    """
    _torch, _Dataset, DataLoader = _import_torch()

    train_w = train_arr.sample_weights if with_sample_weight else None
    train_ds = MultiStockSequenceDataset(
        train_arr.X, train_arr.y, train_arr.stock_ids, sample_weights=train_w
    )
    val_ds = MultiStockSequenceDataset(
        val_arr.X, val_arr.y, val_arr.stock_ids, sample_weights=None
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    return train_loader, val_loader
