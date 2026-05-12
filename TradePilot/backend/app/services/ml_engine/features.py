"""ML 피처 엔지니어링.

OHLCV DataFrame 을 입력으로 받아 MLConfig.features 에 정의된 컬럼들을 생성한다.
시계열 누수(look-ahead bias)를 막기 위해 모든 피처는 t 시점까지의 정보만 사용한다.

피처 변환 규칙:
    - close:    log return (1차 차분, np.log(c_t/c_{t-1}))
    - volume:   log(volume+1) 후 z-score (rolling 미적용; scaler 가 처리)
    - ma5,ma20: close 대비 비율 - 1 (예: close=ma5 면 0)
    - rsi14:    0~100 그대로 (학습 시 scaler 가 정규화)
    - macd:     close 대비 비율로 정규화 (스케일 차이 흡수)
    - bb_pct_b: (close - bb_lower) / (bb_upper - bb_lower) - 1
    - obv:      log(|obv|+1) * sign(obv)

학습 시 누적된 모든 피처에 대해 StandardScaler 를 별도 fit 한다.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.services.backtest_engine.indicators import attach_indicators


def build_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """OHLCV → 피처 DataFrame.

    Args:
        df: index=DatetimeIndex, columns=[open,high,low,close,volume]
        features: MLConfig.features

    Returns:
        DataFrame(columns=features). 워밍업으로 인한 NaN 행은 dropna() 처리됨.
    """
    if df.empty:
        return pd.DataFrame(columns=features)

    # 1) 백테스트 엔진과 동일한 지표 부착 (ma5,ma20,rsi14,macd,bb_*,...)
    enriched = attach_indicators(df)

    out = pd.DataFrame(index=enriched.index)

    for feat in features:
        out[feat] = _compute_feature(feat, enriched)

    # 무한값/NaN 행 제거
    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    return out


def _compute_feature(name: str, df: pd.DataFrame) -> pd.Series:
    """단일 피처 산출."""
    close = df["close"]

    if name == "close":
        # log return
        return np.log(close / close.shift(1))

    if name == "volume":
        # log 거래량 (scaler 에서 z-score 처리)
        return np.log(df["volume"].astype(float) + 1.0)

    if name == "ma5":
        return close / df["ma5"] - 1.0
    if name == "ma20":
        return close / df["ma20"] - 1.0
    if name == "ma60":
        return close / df["ma60"] - 1.0
    if name == "ma120":
        return close / df["ma120"] - 1.0

    if name == "rsi14":
        return df["rsi14"]

    if name == "macd":
        # close 대비 비율로 정규화
        return df["macd"] / close

    if name == "macd_signal":
        return df["macd_signal"] / close

    if name == "macd_hist":
        return df["macd_hist"] / close

    if name == "bb_pct_b":
        upper = df["bb_upper"]
        lower = df["bb_lower"]
        denom = (upper - lower).replace(0, np.nan)
        return (close - lower) / denom

    if name == "obv":
        # OBV 는 누적값이라 시계열 trend 가 강하다 → 일차 차분 후 log scale
        diff = df["close"].diff().fillna(0)
        obv_change = np.sign(diff) * df["volume"].astype(float)
        # log scale (부호 보존)
        return np.sign(obv_change) * np.log(np.abs(obv_change) + 1.0)

    if name == "atr14":
        return df["atr14"] / close

    # 알 수 없는 피처 → 0 채움
    return pd.Series(0.0, index=df.index)


def label_horizon_class(
    close: pd.Series,
    horizon_days: int,
    up_threshold: float,
    down_threshold: float,
) -> pd.Series:
    """horizon 일 후 수익률 기반 3-class 라벨 생성.

    라벨:
        0 = 하락 (r < down_threshold)
        1 = 보합 (down_threshold <= r < up_threshold)
        2 = 상승 (r >= up_threshold)

    수익률은 단순 수익률(simple return) 사용: r = c[t+h] / c[t] - 1
    """
    future = close.shift(-horizon_days)
    ret = future / close - 1.0

    labels = pd.Series(1, index=close.index, dtype="int64")  # 기본 보합
    labels[ret >= up_threshold] = 2
    labels[ret < down_threshold] = 0

    # 미래 데이터가 없는 마지막 horizon_days 행은 NaN
    labels[ret.isna()] = -1
    return labels


def class_weights(labels: np.ndarray, num_classes: int = 3) -> np.ndarray:
    """클래스 불균형 보정용 가중치 (inverse frequency).

    NaN/-1 라벨은 제외한다.
    """
    valid = labels[labels >= 0]
    if len(valid) == 0:
        return np.ones(num_classes, dtype=np.float32)
    counts = np.bincount(valid.astype(int), minlength=num_classes).astype(np.float32)
    # 0 인 클래스는 1 로 대체 (가중치 폭주 방지)
    counts = np.where(counts == 0, 1.0, counts)
    weights = counts.sum() / (num_classes * counts)
    return weights.astype(np.float32)


def summarize_features(df: pd.DataFrame) -> dict[str, Any]:
    """피처 요약 통계 (학습 메타 기록용)."""
    if df.empty:
        return {}
    return {
        "n_rows": int(len(df)),
        "columns": list(df.columns),
        "means": {c: float(df[c].mean()) for c in df.columns},
        "stds": {c: float(df[c].std()) for c in df.columns},
    }
