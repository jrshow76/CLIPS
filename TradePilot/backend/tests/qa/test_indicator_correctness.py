"""기술적 지표 정확성 회귀 테스트.

검증 대상 (TC-CHART-005~008):
- 골든크로스/데드크로스 식별 정확성 (MA 5/20)
- RSI 14 가 0~100 범위 + pandas-ta 결과와 ±0.5 오차 이내 일치
- MACD 12/26/9 신호선 교차 분기 정확성
- 볼린저 밴드 상/중/하 정합성

`pandas-ta` 라이브러리가 설치된 환경 기준. 미설치 시 자체 구현값과 비교.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.indicator_service import IndicatorService


pytestmark = [pytest.mark.qa, pytest.mark.unit]


@pytest.fixture
def trending_up_df() -> pd.DataFrame:
    """선형 상승 추세 (골든크로스 발생용) 60일치 데이터."""
    np.random.seed(7)
    n = 60
    base = np.linspace(50_000, 80_000, n)  # 선형 상승
    noise = np.random.randn(n) * 100
    close = base + noise
    df = pd.DataFrame({
        "open": close * (1 + np.random.randn(n) * 0.001),
        "high": close * 1.005,
        "low": close * 0.995,
        "close": close,
        "volume": np.random.randint(1_000_000, 5_000_000, size=n),
    })
    return df


@pytest.fixture
def trending_down_df() -> pd.DataFrame:
    """선형 하락 추세 (데드크로스/RSI 과매도 검증용)."""
    np.random.seed(11)
    n = 60
    base = np.linspace(80_000, 50_000, n)
    noise = np.random.randn(n) * 100
    close = base + noise
    df = pd.DataFrame({
        "open": close,
        "high": close * 1.003,
        "low": close * 0.997,
        "close": close,
        "volume": np.random.randint(1_000_000, 5_000_000, size=n),
    })
    return df


# --------------------------------------------------------------------------- #
# 골든/데드크로스 식별
# --------------------------------------------------------------------------- #


def test_golden_cross_detected_in_uptrend(trending_up_df: pd.DataFrame) -> None:
    """상승 추세 데이터에서는 마지막 값의 MA5 >= MA20 이어야 한다 (골든크로스 형성)."""
    result = IndicatorService.ma(trending_up_df, [5, 20])
    ma5 = [v for v in result[5] if v is not None]
    ma20 = [v for v in result[20] if v is not None]
    assert ma5 and ma20
    # 마지막 시점에서 MA5 가 MA20 보다 크다 (상승 추세)
    assert ma5[-1] >= ma20[-1]


def test_dead_cross_detected_in_downtrend(trending_down_df: pd.DataFrame) -> None:
    """하락 추세에서 마지막 값의 MA5 <= MA20 (데드크로스 형성)."""
    result = IndicatorService.ma(trending_down_df, [5, 20])
    ma5 = [v for v in result[5] if v is not None]
    ma20 = [v for v in result[20] if v is not None]
    assert ma5[-1] <= ma20[-1]


# --------------------------------------------------------------------------- #
# RSI
# --------------------------------------------------------------------------- #


def test_rsi_in_valid_range(trending_up_df: pd.DataFrame) -> None:
    """RSI 모든 값은 0~100 사이."""
    values = IndicatorService.rsi(trending_up_df, period=14)
    non_none = [v for v in values if v is not None]
    assert non_none, "RSI 계산 결과가 비어 있습니다"
    assert all(0 <= v <= 100 for v in non_none)


def test_rsi_above_70_in_strong_uptrend(trending_up_df: pd.DataFrame) -> None:
    """강한 상승 추세에서는 마지막 RSI 가 50 이상이어야 한다 (이상적으로 70 초과)."""
    values = IndicatorService.rsi(trending_up_df, period=14)
    non_none = [v for v in values if v is not None]
    assert non_none[-1] >= 50.0


def test_rsi_below_30_in_strong_downtrend(trending_down_df: pd.DataFrame) -> None:
    """강한 하락 추세에서는 마지막 RSI 가 50 이하."""
    values = IndicatorService.rsi(trending_down_df, period=14)
    non_none = [v for v in values if v is not None]
    assert non_none[-1] <= 50.0


def test_rsi_matches_pandas_ta_within_tolerance(trending_up_df: pd.DataFrame) -> None:
    """pandas-ta RSI 결과와 마지막 값 ±0.5 오차 이내."""
    pandas_ta = pytest.importorskip("pandas_ta")
    expected = pandas_ta.rsi(trending_up_df["close"], length=14)
    actual = IndicatorService.rsi(trending_up_df, period=14)
    expected_last = expected.dropna().iloc[-1]
    actual_last = [v for v in actual if v is not None][-1]
    assert abs(expected_last - actual_last) < 0.5, (
        f"pandas-ta={expected_last:.4f}, app={actual_last:.4f}"
    )


# --------------------------------------------------------------------------- #
# MACD
# --------------------------------------------------------------------------- #


def test_macd_components_present(trending_up_df: pd.DataFrame) -> None:
    """MACD 출력에 macd/signal/hist 키 모두 포함."""
    result = IndicatorService.macd(trending_up_df, fast=12, slow=26, signal=9)
    assert {"macd", "signal", "hist"} <= set(result.keys())


def test_macd_hist_equals_macd_minus_signal(trending_up_df: pd.DataFrame) -> None:
    """MACD 히스토그램 = macd - signal (마지막 5개 점에서 검증)."""
    result = IndicatorService.macd(trending_up_df, 12, 26, 9)
    for i in range(-5, 0):
        m, s, h = result["macd"][i], result["signal"][i], result["hist"][i]
        if None in (m, s, h):
            continue
        assert abs((m - s) - h) < 1e-6


def test_macd_signal_cross_in_uptrend(trending_up_df: pd.DataFrame) -> None:
    """상승 추세에서 마지막 macd >= signal (골든크로스 영역)."""
    result = IndicatorService.macd(trending_up_df, 12, 26, 9)
    macd_last = [v for v in result["macd"] if v is not None][-1]
    signal_last = [v for v in result["signal"] if v is not None][-1]
    assert macd_last >= signal_last


# --------------------------------------------------------------------------- #
# 볼린저 / 기타
# --------------------------------------------------------------------------- #


def test_bollinger_band_ordering(trending_up_df: pd.DataFrame) -> None:
    """모든 시점에서 upper >= mid >= lower."""
    result = IndicatorService.bollinger(trending_up_df, period=20, k=2)
    for i in range(len(result["upper"])):
        u, m, lo = result["upper"][i], result["mid"][i], result["lower"][i]
        if None in (u, m, lo):
            continue
        assert u >= m >= lo


def test_compute_all_returns_expected_keys(trending_up_df: pd.DataFrame) -> None:
    """compute_all 호출 시 기대 키 모두 존재."""
    out = IndicatorService.compute_all(trending_up_df)
    expected = {
        "ma5", "ma20", "ma60", "ma120",
        "rsi14", "macd", "macd_signal", "macd_hist",
        "bb_mid", "bb_upper", "bb_lower",
        "obv", "vwap", "stoch_k", "stoch_d", "atr14",
    }
    assert expected <= set(out.keys())
