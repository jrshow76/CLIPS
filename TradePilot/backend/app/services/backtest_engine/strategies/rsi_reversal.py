"""RSI 역추세 전략.

진입: RSI <= oversold(기본 30) 영역에서 상향 이탈 시 매수
청산: RSI >= overbought(기본 70) 영역에서 하향 이탈 시 매도
"""
from __future__ import annotations

import pandas as pd

from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import register_strategy


class RsiReversal(Strategy):
    name = "rsi_reversal"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        oversold = float(self.params.get("oversold", 30.0))
        overbought = float(self.params.get("overbought", 70.0))

        rsi = df["rsi14"] if "rsi14" in df.columns else _fallback_rsi(df)
        prev_rsi = rsi.shift(1)

        buy = (prev_rsi <= oversold) & (rsi > oversold)
        sell = (prev_rsi >= overbought) & (rsi < overbought)

        signal = pd.Series(0, index=df.index, dtype="int8")
        signal[buy] = 1
        signal[sell] = -1
        return signal.shift(1).fillna(0).astype("int8")


def _fallback_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """attach_indicators 미적용 시 안전망."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = -delta.clip(upper=0).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return (100 - (100 / (1 + rs))).fillna(50.0)


register_strategy("rsi_reversal", RsiReversal)
