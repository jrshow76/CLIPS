"""IndicatorService 단위 테스트."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.indicator_service import IndicatorService, to_dataframe


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """60일치 OHLCV 더미 데이터."""
    np.random.seed(42)
    n = 60
    base = 70000
    close = base + np.cumsum(np.random.randn(n) * 200)
    df = pd.DataFrame({
        "ts": pd.date_range("2026-01-01", periods=n, freq="D"),
        "open": close * (1 + np.random.randn(n) * 0.005),
        "high": close * (1 + np.abs(np.random.randn(n) * 0.01)),
        "low": close * (1 - np.abs(np.random.randn(n) * 0.01)),
        "close": close,
        "volume": np.random.randint(1_000_000, 5_000_000, size=n),
    })
    df = df.set_index("ts")
    return df


class TestIndicatorService:
    @pytest.mark.unit
    def test_ma_returns_period_keys(self, sample_df: pd.DataFrame) -> None:
        result = IndicatorService.ma(sample_df, [5, 20, 60])
        assert set(result.keys()) == {5, 20, 60}
        assert len(result[5]) == len(sample_df)

    @pytest.mark.unit
    def test_rsi_in_range(self, sample_df: pd.DataFrame) -> None:
        values = IndicatorService.rsi(sample_df, 14)
        assert len(values) == len(sample_df)
        non_none = [v for v in values if v is not None]
        assert all(0 <= v <= 100 for v in non_none)

    @pytest.mark.unit
    def test_macd_components(self, sample_df: pd.DataFrame) -> None:
        result = IndicatorService.macd(sample_df, fast=12, slow=26, signal=9)
        assert set(result.keys()) == {"macd", "signal", "hist"}
        assert len(result["macd"]) == len(sample_df)

    @pytest.mark.unit
    def test_bollinger_upper_gte_mid_gte_lower(self, sample_df: pd.DataFrame) -> None:
        result = IndicatorService.bollinger(sample_df, period=20, k=2)
        # 마지막 5개 샘플 검증
        for i in range(-5, 0):
            u, m, lo = result["upper"][i], result["mid"][i], result["lower"][i]
            if None in (u, m, lo):
                continue
            assert u >= m >= lo

    @pytest.mark.unit
    def test_stochastic_in_range(self, sample_df: pd.DataFrame) -> None:
        result = IndicatorService.stochastic(sample_df)
        for v in result["k"] + result["d"]:
            if v is None:
                continue
            assert 0 <= v <= 100

    @pytest.mark.unit
    def test_compute_all_keys(self, sample_df: pd.DataFrame) -> None:
        out = IndicatorService.compute_all(sample_df)
        expected = {
            "ma5", "ma20", "ma60", "ma120",
            "rsi14", "macd", "macd_signal", "macd_hist",
            "bb_mid", "bb_upper", "bb_lower",
            "obv", "vwap", "stoch_k", "stoch_d", "atr14",
        }
        assert expected <= set(out.keys())

    @pytest.mark.unit
    def test_empty_df_returns_empty(self) -> None:
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        assert IndicatorService.rsi(df) == []
        assert IndicatorService.compute_all(df) == {}

    @pytest.mark.unit
    def test_to_dataframe(self) -> None:
        candles = [
            {"ts": "2026-05-01", "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
            {"ts": "2026-05-02", "open": 105, "high": 115, "low": 100, "close": 112, "volume": 1500},
        ]
        df = to_dataframe(candles)
        assert len(df) == 2
        assert "close" in df.columns
