"""ML 예측 기반 시그널 전략.

`tp_analysis.ml_predictions` 테이블에서 사전에 산출된 예측 결과를 시그널로 사용한다.
백테스트 엔진은 시계열 데이터를 사전 로드하여 vectorized 시그널을 만드는 구조이므로,
ML 예측 결과 또한 strategy_params 의 `predictions` 키로 주입받는다.

params 예시:
    {
        "predictions": {
            "2025-05-12": {"direction": "UP", "confidence": 0.72},
            "2025-05-13": {"direction": "FLAT", "confidence": 0.55},
            ...
        },
        "min_confidence": 0.6,
        "horizon": 3,
        "ensemble": true                  # True 이면 앙상블 예측을 우선 사용
    }

또는 model_version 문자열로부터 파싱하는 경우 `predictions_df` 키 (DataFrame)를 직접 주입.

시그널 규칙 (기본):
    direction=UP   AND confidence >= min_conf  → 매수(1)
    direction=DOWN AND confidence >= min_conf  → 매도(-1)
    그 외(FLAT 또는 신뢰도 미달)               → 홀드(0)

엔진 호환을 위해 시그널은 한 칸 shift (look-ahead 방지).

ensemble=True 의 의미:
    params 에 `ensemble_predictions` 키가 별도로 있으면 그쪽을 우선 사용한다.
    없으면 `predictions` 를 그대로 사용 (호환). 즉 백테스트는 사전에 산출된
    앙상블 예측을 주입받는 구조다 (가격 시계열 외부에서 미리 ensemble 호출).
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import register_strategy


class MLSignalStrategy(Strategy):
    """ML 예측 결과 기반 매매 시그널."""

    name = "ml_signal"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        ensemble = bool(self.params.get("ensemble", False))
        # ensemble=True 면 ensemble_predictions 키를 우선 사용
        if ensemble and self.params.get("ensemble_predictions"):
            predictions: dict[str, Any] = self.params["ensemble_predictions"]
        else:
            predictions = self.params.get("predictions") or {}
        min_conf = float(self.params.get("min_confidence", 0.6))

        signal = pd.Series(0, index=df.index, dtype="int8")

        if not predictions:
            return signal

        # 인덱스(date) 매핑
        for ts in df.index:
            key = _date_key(ts)
            entry = predictions.get(key)
            if not entry:
                continue
            direction = str(entry.get("direction", "FLAT")).upper()
            conf = float(entry.get("confidence", 0.0))
            if conf < min_conf:
                continue
            if direction == "UP":
                signal.loc[ts] = 1
            elif direction == "DOWN":
                signal.loc[ts] = -1

        # 다음 거래일 체결 가정 (백테스트 엔진 관례)
        return signal.shift(1).fillna(0).astype("int8")


def _date_key(ts: Any) -> str:
    """DatetimeIndex 원소 → 'YYYY-MM-DD' 문자열."""
    if isinstance(ts, pd.Timestamp):
        return ts.date().isoformat()
    if isinstance(ts, date):
        return ts.isoformat()
    return str(ts)[:10]


def eval_ml_predict_rule(rule: dict[str, Any], df: pd.DataFrame) -> pd.Series:
    """Composite DSL 의 `ml_predict` 룰 평가.

    rule 예시:
        {"type": "ml_predict", "horizon": 3, "min_confidence": 0.6, "direction": "UP"}
        {"type": "ml_predict", "horizon": 1, "min_confidence": 0.5, "direction": "DOWN"}
        {"type": "ml_predict", "horizon": 3, "min_confidence": 0.6, "ensemble": true}

    사용 가능한 입력 채널 (params 와 동일):
        df.attrs["ml_predictions"] = {"YYYY-MM-DD": {"direction": "UP", "confidence": 0.72}}
        df.attrs["ml_ensemble_predictions"] = {...}  # ensemble=true 일 때 우선 사용

    DataFrame.attrs 에 예측이 부착되지 않은 경우 모든 행 False.
    """
    target_direction = str(rule.get("direction", "UP")).upper()
    min_conf = float(rule.get("min_confidence", 0.6))
    use_ensemble = bool(rule.get("ensemble", False))
    attrs = df.attrs or {}
    if use_ensemble and attrs.get("ml_ensemble_predictions"):
        predictions = attrs["ml_ensemble_predictions"]
    else:
        predictions = attrs.get("ml_predictions") or {}

    if not predictions:
        return pd.Series(False, index=df.index)

    mask_values: list[bool] = []
    for ts in df.index:
        key = _date_key(ts)
        entry = predictions.get(key)
        if not entry:
            mask_values.append(False)
            continue
        direction = str(entry.get("direction", "FLAT")).upper()
        conf = float(entry.get("confidence", 0.0))
        mask_values.append(direction == target_direction and conf >= min_conf)
    return pd.Series(mask_values, index=df.index)


register_strategy("ml_signal", MLSignalStrategy)
