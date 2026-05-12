"""DSL/strategy_rules 기반 복합 전략.

DB의 `tp_trade.strategies.entry_rules / exit_rules` JSONB 또는
`tp_trade.strategy_rules` 의 정규화된 행을 받아 시그널을 산출한다.

지원 DSL (entry/exit_rules JSONB):
    {
      "all": [           # AND 조합
        {"indicator": "RSI", "op": "<", "value": 30},
        {"indicator": "MA",  "op": "CROSS_UP", "fast": 5, "slow": 20}
      ]
    }
또는 {"any": [...]} (OR 조합), 중첩도 지원한다.

지원 indicator: RSI, MA, MACD, BB, CLOSE
지원 op: <, <=, >, >=, =, CROSS_UP, CROSS_DOWN
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import register_strategy


class Composite(Strategy):
    name = "composite"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self.entry_rules: dict[str, Any] = self.params.get("entry_rules", {}) or {}
        self.exit_rules: dict[str, Any] = self.params.get("exit_rules", {}) or {}

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        entry_mask = _eval_rules(self.entry_rules, df) if self.entry_rules else pd.Series(False, index=df.index)
        exit_mask = _eval_rules(self.exit_rules, df) if self.exit_rules else pd.Series(False, index=df.index)

        signal = pd.Series(0, index=df.index, dtype="int8")
        signal[entry_mask] = 1
        signal[exit_mask] = -1
        # 진입과 청산이 동시에 True 라면 청산 우선 (보수적)
        signal[entry_mask & exit_mask] = -1
        return signal.shift(1).fillna(0).astype("int8")


# ----------------------------------------------------------------------------
# DSL 평가기
# ----------------------------------------------------------------------------
def _eval_rules(node: dict[str, Any], df: pd.DataFrame) -> pd.Series:
    """DSL 트리를 평가해 boolean Series 반환."""
    if "all" in node:
        children = node["all"]
        masks = [_eval_rules(c, df) for c in children]
        return _combine_and(masks, df.index)
    if "any" in node:
        children = node["any"]
        masks = [_eval_rules(c, df) for c in children]
        return _combine_or(masks, df.index)
    return _eval_atom(node, df)


def _combine_and(masks: list[pd.Series], index: pd.Index) -> pd.Series:
    if not masks:
        return pd.Series(False, index=index)
    result = masks[0]
    for m in masks[1:]:
        result = result & m
    return result


def _combine_or(masks: list[pd.Series], index: pd.Index) -> pd.Series:
    if not masks:
        return pd.Series(False, index=index)
    result = masks[0]
    for m in masks[1:]:
        result = result | m
    return result


def _eval_atom(rule: dict[str, Any], df: pd.DataFrame) -> pd.Series:
    """단일 룰 평가."""
    indicator = str(rule.get("indicator", "")).upper()
    op = str(rule.get("op", "")).upper()
    value = rule.get("value")

    series = _resolve_series(indicator, rule, df)
    if series is None:
        return pd.Series(False, index=df.index)

    if op in ("<", "LT"):
        return series < float(value)
    if op in ("<=", "LTE"):
        return series <= float(value)
    if op in (">", "GT"):
        return series > float(value)
    if op in (">=", "GTE"):
        return series >= float(value)
    if op in ("=", "==", "EQ"):
        return np.isclose(series, float(value))
    if op == "CROSS_UP":
        ref = _resolve_reference(rule, df, default=float(value) if value is not None else None)
        if ref is None:
            return pd.Series(False, index=df.index)
        diff = series - ref
        return (diff.shift(1) <= 0) & (diff > 0)
    if op == "CROSS_DOWN":
        ref = _resolve_reference(rule, df, default=float(value) if value is not None else None)
        if ref is None:
            return pd.Series(False, index=df.index)
        diff = series - ref
        return (diff.shift(1) >= 0) & (diff < 0)
    return pd.Series(False, index=df.index)


def _resolve_series(indicator: str, rule: dict[str, Any], df: pd.DataFrame) -> pd.Series | None:
    """indicator → 비교 대상 시리즈."""
    if indicator == "RSI":
        return df.get("rsi14")
    if indicator == "CLOSE":
        return df.get("close")
    if indicator == "MA":
        period = int(rule.get("period", rule.get("fast", 5)))
        col = f"ma{period}"
        if col in df.columns:
            return df[col]
        return df["close"].rolling(window=period, min_periods=1).mean()
    if indicator == "MACD":
        return df.get("macd")
    if indicator == "BB_UPPER":
        return df.get("bb_upper")
    if indicator == "BB_LOWER":
        return df.get("bb_lower")
    if indicator == "VOLUME":
        return df.get("volume")
    return None


def _resolve_reference(rule: dict[str, Any], df: pd.DataFrame, default: float | None) -> pd.Series | float | None:
    """CROSS_UP/DOWN 의 비교 기준선.

    `vs_indicator` 또는 `slow` 키가 있으면 시리즈, 없으면 default(상수) 사용.
    예: {"indicator": "MA", "fast":5, "op":"CROSS_UP", "slow": 20}
    """
    if "vs_indicator" in rule:
        return _resolve_series(str(rule["vs_indicator"]).upper(), rule, df)
    if "slow" in rule:
        slow = int(rule["slow"])
        col = f"ma{slow}"
        if col in df.columns:
            return df[col]
        return df["close"].rolling(window=slow, min_periods=1).mean()
    return default


register_strategy("composite", Composite)
