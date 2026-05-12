"""볼린저 밴드 전략.

mode='breakout': 상단 돌파 매수, 하단 돌파 매도 (추세추종)
mode='reversion'(기본): 하단 터치 후 회귀 매수, 상단 터치 후 회귀 매도 (역추세)
"""
from __future__ import annotations

import pandas as pd

from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import register_strategy


class BollingerBreakout(Strategy):
    name = "bollinger_breakout"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        mode = str(self.params.get("mode", "reversion"))
        close = df["close"]
        upper = df["bb_upper"] if "bb_upper" in df.columns else _fallback_bb(df, "upper")
        lower = df["bb_lower"] if "bb_lower" in df.columns else _fallback_bb(df, "lower")

        prev_close = close.shift(1)
        signal = pd.Series(0, index=df.index, dtype="int8")

        if mode == "breakout":
            buy = (prev_close <= upper.shift(1)) & (close > upper)
            sell = (prev_close >= lower.shift(1)) & (close < lower)
        else:  # reversion
            # 하단을 이탈했다가 다시 복귀 → 매수
            buy = (prev_close < lower.shift(1)) & (close >= lower)
            # 상단을 이탈했다가 다시 복귀 → 매도
            sell = (prev_close > upper.shift(1)) & (close <= upper)

        signal[buy] = 1
        signal[sell] = -1
        return signal.shift(1).fillna(0).astype("int8")


def _fallback_bb(df: pd.DataFrame, kind: str, period: int = 20, k: float = 2.0) -> pd.Series:
    mid = df["close"].rolling(window=period, min_periods=1).mean()
    std = df["close"].rolling(window=period, min_periods=1).std(ddof=0)
    return mid + k * std if kind == "upper" else mid - k * std


register_strategy("bollinger_breakout", BollingerBreakout)
