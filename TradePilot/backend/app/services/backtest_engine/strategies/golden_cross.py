"""골든크로스 / 데드크로스 전략.

진입: 단기 MA(기본 5)가 장기 MA(기본 20) 를 상향 돌파한 다음 캔들
청산: 단기 MA 가 장기 MA 를 하향 돌파한 다음 캔들

look-ahead bias 방지를 위해 시그널은 다음 거래일에 발생하도록 shift(1) 한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import register_strategy


class GoldenCross(Strategy):
    name = "golden_cross"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = int(self.params.get("fast", 5))
        slow = int(self.params.get("slow", 20))

        if fast == 5 and slow == 20 and "ma5" in df.columns and "ma20" in df.columns:
            ma_fast = df["ma5"]
            ma_slow = df["ma20"]
        else:
            ma_fast = df["close"].rolling(window=fast, min_periods=1).mean()
            ma_slow = df["close"].rolling(window=slow, min_periods=1).mean()

        diff = ma_fast - ma_slow
        prev_diff = diff.shift(1)

        cross_up = (prev_diff <= 0) & (diff > 0)
        cross_down = (prev_diff >= 0) & (diff < 0)

        signal = pd.Series(0, index=df.index, dtype="int8")
        signal[cross_up] = 1
        signal[cross_down] = -1

        # 다음 거래일 체결 가정: 시그널을 한 칸 미룬다.
        return signal.shift(1).fillna(0).astype("int8")


register_strategy("golden_cross", GoldenCross)
