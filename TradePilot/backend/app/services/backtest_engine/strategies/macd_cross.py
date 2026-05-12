"""MACD 시그널 라인 교차 전략.

진입: MACD 라인이 시그널 라인을 상향 돌파
청산: MACD 라인이 시그널 라인을 하향 돌파
"""
from __future__ import annotations

import pandas as pd

from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import register_strategy


class MacdCross(Strategy):
    name = "macd_cross"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if "macd" not in df.columns or "macd_signal" not in df.columns:
            # 안전망: 즉석 계산
            ema_fast = df["close"].ewm(span=12, adjust=False).mean()
            ema_slow = df["close"].ewm(span=26, adjust=False).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=9, adjust=False).mean()
        else:
            macd = df["macd"]
            signal_line = df["macd_signal"]

        diff = macd - signal_line
        prev_diff = diff.shift(1)

        buy = (prev_diff <= 0) & (diff > 0)
        sell = (prev_diff >= 0) & (diff < 0)

        signal = pd.Series(0, index=df.index, dtype="int8")
        signal[buy] = 1
        signal[sell] = -1
        return signal.shift(1).fillna(0).astype("int8")


register_strategy("macd_cross", MacdCross)
