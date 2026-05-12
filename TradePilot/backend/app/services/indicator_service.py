"""기술적 지표 계산 서비스.

pandas-ta 기반. (TA-Lib 미사용)
산출 지표:
- MA(5/20/60/120), RSI(14), MACD(12/26/9), Bollinger(20,2)
- OBV, VWAP, Stochastic(14/3/3), ATR(14)

`docs/13_api_requirements.md` §4 명세 + DDL `indicators_daily`와 일치한다.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog

try:
    import pandas_ta as ta  # type: ignore
    HAS_PANDAS_TA = True
except Exception:  # pragma: no cover - pandas-ta 미설치 환경
    ta = None
    HAS_PANDAS_TA = False

log = structlog.get_logger(__name__)


def to_dataframe(candles: list[dict[str, Any]]) -> pd.DataFrame:
    """OHLCV 리스트 → DataFrame.

    candles: [{ts, open, high, low, close, volume}, ...]
    """
    if not candles:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])
    df = pd.DataFrame(candles)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.set_index("ts")
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_index()


class IndicatorService:
    """지표 계산. 정적 메서드 모음 형태로 사용."""

    # ------------------------------------------------------------------
    # 단일 지표
    # ------------------------------------------------------------------
    @staticmethod
    def ma(df: pd.DataFrame, periods: list[int]) -> dict[int, list[float | None]]:
        """이동평균. {period: [values]} 반환."""
        result: dict[int, list[float | None]] = {}
        if df.empty:
            return {p: [] for p in periods}
        for p in periods:
            series = df["close"].rolling(window=p, min_periods=1).mean()
            result[p] = [None if np.isnan(v) else float(v) for v in series.values]
        return result

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> list[float | None]:
        if df.empty:
            return []
        if HAS_PANDAS_TA:
            series = ta.rsi(df["close"], length=period)
        else:
            # 직접 계산 (Wilder's RSI)
            delta = df["close"].diff()
            gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
            loss = -delta.clip(upper=0).rolling(window=period, min_periods=period).mean()
            rs = gain / loss.replace(0, np.nan)
            series = 100 - (100 / (1 + rs))
        return [None if pd.isna(v) else float(v) for v in series]

    @staticmethod
    def macd(
        df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> dict[str, list[float | None]]:
        if df.empty:
            return {"macd": [], "signal": [], "hist": []}
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        return {
            "macd": [None if pd.isna(v) else float(v) for v in macd_line],
            "signal": [None if pd.isna(v) else float(v) for v in signal_line],
            "hist": [None if pd.isna(v) else float(v) for v in hist],
        }

    @staticmethod
    def bollinger(
        df: pd.DataFrame, period: int = 20, k: float = 2.0
    ) -> dict[str, list[float | None]]:
        if df.empty:
            return {"mid": [], "upper": [], "lower": []}
        mid = df["close"].rolling(window=period, min_periods=1).mean()
        std = df["close"].rolling(window=period, min_periods=1).std(ddof=0)
        upper = mid + k * std
        lower = mid - k * std
        return {
            "mid": [None if pd.isna(v) else float(v) for v in mid],
            "upper": [None if pd.isna(v) else float(v) for v in upper],
            "lower": [None if pd.isna(v) else float(v) for v in lower],
        }

    @staticmethod
    def obv(df: pd.DataFrame) -> list[float | None]:
        if df.empty or "volume" not in df.columns:
            return []
        direction = np.sign(df["close"].diff().fillna(0))
        obv_series = (direction * df["volume"]).cumsum()
        return [None if pd.isna(v) else float(v) for v in obv_series]

    @staticmethod
    def vwap(df: pd.DataFrame) -> list[float | None]:
        if df.empty or "volume" not in df.columns:
            return []
        tp = (df["high"] + df["low"] + df["close"]) / 3
        vwap_series = (tp * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, np.nan)
        return [None if pd.isna(v) else float(v) for v in vwap_series]

    @staticmethod
    def stochastic(
        df: pd.DataFrame, k_period: int = 14, d_period: int = 3, smooth: int = 3
    ) -> dict[str, list[float | None]]:
        if df.empty:
            return {"k": [], "d": []}
        low_min = df["low"].rolling(window=k_period, min_periods=1).min()
        high_max = df["high"].rolling(window=k_period, min_periods=1).max()
        denom = (high_max - low_min).replace(0, np.nan)
        raw_k = (df["close"] - low_min) / denom * 100
        k = raw_k.rolling(window=smooth, min_periods=1).mean()
        d = k.rolling(window=d_period, min_periods=1).mean()
        return {
            "k": [None if pd.isna(v) else float(v) for v in k],
            "d": [None if pd.isna(v) else float(v) for v in d],
        }

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> list[float | None]:
        if df.empty:
            return []
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr_series = tr.rolling(window=period, min_periods=1).mean()
        return [None if pd.isna(v) else float(v) for v in atr_series]

    # ------------------------------------------------------------------
    # 일괄 지표 (indicators_daily 캐시 산출용)
    # ------------------------------------------------------------------
    @classmethod
    def compute_all(cls, df: pd.DataFrame) -> dict[str, Any]:
        """모든 지표를 한 번에 계산하고 가장 최근 1행 결과를 반환한다."""
        if df.empty:
            return {}
        ma_dict = cls.ma(df, [5, 20, 60, 120])
        rsi14 = cls.rsi(df, 14)
        macd_dict = cls.macd(df)
        bb = cls.bollinger(df)
        obv = cls.obv(df)
        vwap = cls.vwap(df)
        stoch = cls.stochastic(df)
        atr14 = cls.atr(df, 14)

        def last(values: list[Any]) -> Any:
            return values[-1] if values else None

        return {
            "ma5": last(ma_dict.get(5, [])),
            "ma20": last(ma_dict.get(20, [])),
            "ma60": last(ma_dict.get(60, [])),
            "ma120": last(ma_dict.get(120, [])),
            "rsi14": last(rsi14),
            "macd": last(macd_dict["macd"]),
            "macd_signal": last(macd_dict["signal"]),
            "macd_hist": last(macd_dict["hist"]),
            "bb_mid": last(bb["mid"]),
            "bb_upper": last(bb["upper"]),
            "bb_lower": last(bb["lower"]),
            "obv": last(obv),
            "vwap": last(vwap),
            "stoch_k": last(stoch["k"]),
            "stoch_d": last(stoch["d"]),
            "atr14": last(atr14),
        }
