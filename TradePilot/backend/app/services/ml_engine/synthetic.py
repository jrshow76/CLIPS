"""ML 엔진 합성 시계열 생성기.

DB 가 없는 단위테스트/CI 환경에서도 학습/추론 파이프라인을 검증하기 위한
재현 가능한(seed 고정) OHLCV 시계열을 생성한다.

`backtest_engine/data_loader._synthetic_series` 와 동일한 GBM 형태를 사용하되,
ML 학습용으로 더 긴 기간(기본 3년)을 생성한다.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd


def make_synthetic_ohlcv(
    code: str = "TEST",
    start: date | None = None,
    days: int = 600,
    seed: int | None = None,
    drift: float = 0.0003,
    vol: float = 0.018,
) -> pd.DataFrame:
    """평일 기반 합성 OHLCV 시계열 생성.

    Args:
        code: 시드 분기용 종목코드 (고정 seed 와 결합)
        start: 시작일 (None 이면 today - days*1.5)
        days: 생성할 거래일 수 (평일 기준)
        seed: 명시 seed (None 이면 code 해시)
        drift: 일간 추세 (log return 평균)
        vol: 일간 변동성 (log return 표준편차)

    Returns:
        DataFrame(index=trade_date, columns=[open, high, low, close, volume])
    """
    if seed is None:
        seed = abs(hash(code)) % (2**32)
    rng = np.random.default_rng(seed=seed)

    if start is None:
        start = date.today() - timedelta(days=int(days * 1.6))

    # 평일만 채워서 days 개 생성
    dates: list[date] = []
    d = start
    while len(dates) < days:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)

    n = len(dates)
    base_price = float(rng.integers(20_000, 100_000))
    returns = rng.normal(loc=drift, scale=vol, size=n)
    close = base_price * np.exp(np.cumsum(returns))
    open_ = np.concatenate([[base_price], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.005, n)))
    volume = rng.integers(100_000, 5_000_000, size=n).astype("int64")

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=pd.to_datetime(dates),
    )
    df.index.name = "trade_date"
    return df


def make_regime_switching_series(
    code: str = "TEST",
    days: int = 600,
    seed: int | None = None,
) -> pd.DataFrame:
    """체제 전환(regime switching) 합성 시계열.

    상승/횡보/하락 체제를 번갈아가며 생성한다. 학습 효과를 확인할 수 있는
    "예측 가능한" 패턴을 일부 포함한다.
    """
    if seed is None:
        seed = abs(hash(code)) % (2**32)
    rng = np.random.default_rng(seed=seed)

    segments = []
    remaining = days
    while remaining > 0:
        seg_len = int(rng.integers(40, 90))
        seg_len = min(seg_len, remaining)
        regime = rng.integers(0, 3)  # 0=하락, 1=횡보, 2=상승
        if regime == 0:
            drift, vol = -0.002, 0.018
        elif regime == 1:
            drift, vol = 0.0, 0.012
        else:
            drift, vol = 0.002, 0.018
        segments.append(rng.normal(loc=drift, scale=vol, size=seg_len))
        remaining -= seg_len

    returns = np.concatenate(segments)
    n = len(returns)
    base = float(rng.integers(30_000, 80_000))
    close = base * np.exp(np.cumsum(returns))
    open_ = np.concatenate([[base], close[:-1]])
    high = np.maximum(open_, close) * 1.005
    low = np.minimum(open_, close) * 0.995
    volume = rng.integers(100_000, 3_000_000, size=n).astype("int64")

    start = date.today() - timedelta(days=int(n * 1.6))
    dates: list[date] = []
    d = start
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)

    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=pd.to_datetime(dates),
    )
    df.index.name = "trade_date"
    return df
