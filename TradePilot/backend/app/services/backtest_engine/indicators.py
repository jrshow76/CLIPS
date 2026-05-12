"""백테스트 지표 사전 계산 헬퍼.

`IndicatorService` 는 시점별 마지막 값을 반환하는 형태도 있어 백테스트에는 비효율적이다.
여기서는 전체 시계열 길이의 Series 를 한 번에 계산해 DataFrame 에 부착한다(vectorized).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def attach_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV DataFrame 에 백테스트에서 자주 쓰는 지표 컬럼을 추가한다.

    추가 컬럼:
        ma5, ma20, ma60, ma120
        rsi14
        macd, macd_signal, macd_hist
        bb_mid, bb_upper, bb_lower
        atr14
    """
    if df.empty:
        return df.copy()

    out = df.copy()
    close = out["close"]

    # 이동평균
    out["ma5"] = close.rolling(window=5, min_periods=1).mean()
    out["ma20"] = close.rolling(window=20, min_periods=1).mean()
    out["ma60"] = close.rolling(window=60, min_periods=1).mean()
    out["ma120"] = close.rolling(window=120, min_periods=1).mean()

    # RSI (Wilder's, 14)
    out["rsi14"] = _rsi(close, period=14)

    # MACD (12, 26, 9)
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    out["macd"] = macd_line
    out["macd_signal"] = signal_line
    out["macd_hist"] = macd_line - signal_line

    # Bollinger (20, 2)
    mid = close.rolling(window=20, min_periods=1).mean()
    std = close.rolling(window=20, min_periods=1).std(ddof=0)
    out["bb_mid"] = mid
    out["bb_upper"] = mid + 2.0 * std
    out["bb_lower"] = mid - 2.0 * std

    # ATR (14)
    high_low = out["high"] - out["low"]
    high_close = (out["high"] - close.shift()).abs()
    low_close = (out["low"] - close.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(window=14, min_periods=1).mean()

    return out


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI 벡터화 구현."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)  # 워밍업 구간은 중립값
