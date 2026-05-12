"""백테스트 전략 추상 기반."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class Strategy(ABC):
    """전략 베이스.

    `generate_signals(df) -> pd.Series` 를 구현한다.
    반환 시리즈:
        index: DatetimeIndex (df 의 인덱스와 동일)
        value: 1 = 매수, -1 = 매도, 0 = 홀드

    엔진은 `attach_indicators` 가 적용된 DataFrame 을 입력으로 전달한다.
    """

    name: str = "base"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params: dict[str, Any] = params or {}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """시그널 시리즈 생성."""
        raise NotImplementedError
