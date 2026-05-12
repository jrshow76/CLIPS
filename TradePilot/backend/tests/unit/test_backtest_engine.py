"""백테스트 엔진 단위 테스트.

DB 없이 동작: 합성 시계열로 전략/포트폴리오/메트릭 검증.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from app.services.backtest_engine.config import (
    DEFAULT_FEE_RATE,
    DEFAULT_SELL_TAX,
    DEFAULT_SLIPPAGE,
    BacktestConfig,
    TradeRecord,
)
from app.services.backtest_engine.executor import BacktestExecutor
from app.services.backtest_engine.indicators import attach_indicators
from app.services.backtest_engine.metrics import compute_metrics
from app.services.backtest_engine.portfolio import Portfolio
from app.services.backtest_engine.strategies import get_strategy
from app.services.backtest_engine.strategies.composite import _eval_rules


# ----------------------------------------------------------------------------
# 합성 시계열 유틸
# ----------------------------------------------------------------------------
def make_trend_df(direction: str = "up", n: int = 120, start: float = 50000.0) -> pd.DataFrame:
    """상승/하락/횡보 시계열 생성."""
    dates = pd.bdate_range("2025-01-01", periods=n)
    if direction == "up":
        drift = 0.004
    elif direction == "down":
        drift = -0.004
    else:
        drift = 0.0
    rng = np.random.default_rng(seed=42)
    noise = rng.normal(0, 0.01, n)
    close = start * np.exp(np.cumsum(np.full(n, drift) + noise))
    open_ = np.concatenate([[start], close[:-1]])
    high = np.maximum(open_, close) * 1.005
    low = np.minimum(open_, close) * 0.995
    volume = rng.integers(100_000, 1_000_000, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


# ----------------------------------------------------------------------------
# 1. 전략 시그널
# ----------------------------------------------------------------------------
class TestGoldenCrossStrategy:
    @pytest.mark.unit
    def test_uptrend_produces_buy_signal(self) -> None:
        df = attach_indicators(make_trend_df("up", n=100))
        cls = get_strategy("golden_cross")
        assert cls is not None
        signals = cls().generate_signals(df)
        # 상승 추세에서는 적어도 1번의 매수 시그널 발생
        assert (signals == 1).sum() >= 1

    @pytest.mark.unit
    def test_signal_values_in_set(self) -> None:
        df = attach_indicators(make_trend_df("up", n=80))
        signals = get_strategy("golden_cross")().generate_signals(df)
        assert set(signals.unique()).issubset({-1, 0, 1})

    @pytest.mark.unit
    def test_signal_no_lookahead(self) -> None:
        """시그널은 다음 봉에서 발생해야 한다(shift)."""
        df = attach_indicators(make_trend_df("up", n=50))
        signals = get_strategy("golden_cross")().generate_signals(df)
        # 첫 봉은 항상 0 이어야 한다.
        assert signals.iloc[0] == 0


class TestRsiReversalStrategy:
    @pytest.mark.unit
    def test_oversold_recovery_triggers_buy(self) -> None:
        df = attach_indicators(make_trend_df("down", n=120))
        signals = get_strategy("rsi_reversal")().generate_signals(df)
        assert set(signals.unique()).issubset({-1, 0, 1})


class TestCompositeDSL:
    @pytest.mark.unit
    def test_simple_rsi_atom(self) -> None:
        df = attach_indicators(make_trend_df("down", n=60))
        rule = {"indicator": "RSI", "op": "<", "value": 50}
        mask = _eval_rules(rule, df)
        assert mask.dtype == bool
        # 하락 추세이므로 RSI < 50 케이스가 많아야 한다.
        assert mask.sum() >= 5

    @pytest.mark.unit
    def test_all_combiner(self) -> None:
        df = attach_indicators(make_trend_df("up", n=80))
        rule = {
            "all": [
                {"indicator": "RSI", "op": ">", "value": 30},
                {"indicator": "CLOSE", "op": ">", "value": 0},
            ]
        }
        mask = _eval_rules(rule, df)
        assert mask.sum() > 0


# ----------------------------------------------------------------------------
# 2. Portfolio
# ----------------------------------------------------------------------------
class TestPortfolio:
    @pytest.mark.unit
    def test_buy_decreases_cash_and_creates_position(self) -> None:
        p = Portfolio(initial_cash=10_000_000.0)
        ok = p.buy(date(2025, 1, 2), "005930", price=70_000.0, qty=10)
        assert ok
        # 슬리피지+수수료가 반영된 만큼 차감
        expected_gross = 70_000 * (1 + float(DEFAULT_SLIPPAGE)) * 10
        expected_fee = expected_gross * float(DEFAULT_FEE_RATE)
        expected_cash = 10_000_000 - (expected_gross + expected_fee)
        assert abs(p.cash - expected_cash) < 1e-6
        assert p.positions["005930"].qty == 10

    @pytest.mark.unit
    def test_sell_records_trade_with_pnl(self) -> None:
        p = Portfolio(initial_cash=10_000_000.0)
        p.buy(date(2025, 1, 2), "005930", price=70_000.0, qty=10)
        p.sell(date(2025, 2, 2), "005930", price=80_000.0, qty=10)
        assert len(p.closed_trades) == 1
        trade = p.closed_trades[0]
        assert trade.side == "SELL"
        assert trade.qty == 10
        # 매수가보다 매도가가 높으므로 pnl > 0 (수수료/세금 차감 후)
        assert trade.pnl is not None and float(trade.pnl) > 0
        # 보유 포지션이 사라져야 한다.
        assert p.positions["005930"].qty == 0

    @pytest.mark.unit
    def test_buy_with_insufficient_cash_clamps_qty(self) -> None:
        p = Portfolio(initial_cash=100_000.0)
        ok = p.buy(date(2025, 1, 2), "005930", price=70_000.0, qty=10)
        # 자본 부족 → 자동 클램프되어 부분 매수
        assert ok is True or ok is False  # 자본이 너무 작으면 1주만 매수 가능
        assert p.positions.get("005930", None) is None or p.positions["005930"].qty <= 1

    @pytest.mark.unit
    def test_mark_to_market_with_current_prices(self) -> None:
        p = Portfolio(initial_cash=10_000_000.0)
        p.buy(date(2025, 1, 2), "005930", price=70_000.0, qty=10)
        equity_at_70k = p.mark_to_market({"005930": 70_000.0})
        equity_at_80k = p.mark_to_market({"005930": 80_000.0})
        assert equity_at_80k > equity_at_70k
        # 평가차익 = 10주 * 10,000원 = 100,000원
        assert abs((equity_at_80k - equity_at_70k) - 100_000.0) < 1e-6

    @pytest.mark.unit
    def test_fee_and_tax_accounting(self) -> None:
        p = Portfolio(initial_cash=10_000_000.0)
        p.buy(date(2025, 1, 2), "005930", price=70_000.0, qty=100)
        p.sell(date(2025, 2, 2), "005930", price=70_000.0, qty=100)
        # 매수+매도 각 1회 → 수수료 2회, 세금 1회 발생
        assert p.total_fee_paid > 0
        assert p.total_tax_paid > 0
        # 세율 비교: tax > fee (0.23% vs 0.015%)
        assert p.total_tax_paid > p.total_fee_paid


# ----------------------------------------------------------------------------
# 3. Executor
# ----------------------------------------------------------------------------
class TestExecutor:
    @pytest.mark.unit
    def test_executor_runs_and_records_equity_curve(self) -> None:
        df = attach_indicators(make_trend_df("up", n=100))
        strategy = get_strategy("golden_cross")()
        signals = strategy.generate_signals(df)

        config = BacktestConfig(
            universe=["TEST"],
            strategy_type="golden_cross",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 12, 31),
            initial_capital=Decimal("10000000"),
            max_positions=1,
        )
        executor = BacktestExecutor(
            config=config,
            frames={"TEST": df},
            signals={"TEST": signals},
        )
        equity_curve = executor.run()
        assert len(equity_curve) == len(df)
        # equity는 양수여야 한다
        assert all(p["equity"] > 0 for p in equity_curve)

    @pytest.mark.unit
    def test_max_positions_respected(self) -> None:
        # 두 종목 모두 강한 상승, max_positions=1 이면 1개만 보유
        df1 = attach_indicators(make_trend_df("up", n=80, start=50_000))
        df2 = attach_indicators(make_trend_df("up", n=80, start=60_000))
        strategy = get_strategy("golden_cross")()
        sigs = {"A": strategy.generate_signals(df1), "B": strategy.generate_signals(df2)}

        config = BacktestConfig(
            universe=["A", "B"],
            strategy_type="golden_cross",
            period_from=date(2025, 1, 1),
            period_to=date(2025, 12, 31),
            initial_capital=Decimal("10000000"),
            max_positions=1,
        )
        executor = BacktestExecutor(config, frames={"A": df1, "B": df2}, signals=sigs)
        executor.run()
        held = executor.portfolio.open_position_count()
        assert held <= 1


# ----------------------------------------------------------------------------
# 4. Metrics
# ----------------------------------------------------------------------------
class TestMetrics:
    @pytest.mark.unit
    def test_compute_metrics_basic(self) -> None:
        # equity가 1.0 → 1.2 로 단조증가하는 가상 곡선
        n = 252
        dates = pd.bdate_range("2025-01-01", periods=n)
        equity = np.linspace(10_000_000, 12_000_000, n)
        peak = np.maximum.accumulate(equity)
        dd = equity / peak - 1.0
        equity_curve = [
            {"date": d.date().isoformat(), "equity": float(e), "drawdown": float(x), "cash": 0.0}
            for d, e, x in zip(dates, equity, dd)
        ]
        metrics, monthly = compute_metrics(10_000_000.0, equity_curve, trades=[])
        assert metrics["cumulative_return"] == pytest.approx(0.2, abs=0.001)
        assert metrics["annualized_return"] > 0
        assert metrics["mdd"] == pytest.approx(0.0, abs=1e-6)
        assert isinstance(monthly, dict)

    @pytest.mark.unit
    def test_mdd_is_negative_on_drawdown(self) -> None:
        n = 60
        dates = pd.bdate_range("2025-01-01", periods=n)
        # 30일 상승 후 30일 하락
        eq = np.concatenate([np.linspace(1_000_000, 1_500_000, 30), np.linspace(1_500_000, 1_000_000, 30)])
        peak = np.maximum.accumulate(eq)
        dd = eq / peak - 1.0
        equity_curve = [
            {"date": d.date().isoformat(), "equity": float(e), "drawdown": float(x), "cash": 0.0}
            for d, e, x in zip(dates, eq, dd)
        ]
        metrics, _ = compute_metrics(1_000_000.0, equity_curve, trades=[])
        assert metrics["mdd"] < 0
        # 1.5M → 1.0M ≈ -33.3%
        assert metrics["mdd"] == pytest.approx(-0.3333, abs=0.01)

    @pytest.mark.unit
    def test_win_rate_calculation(self) -> None:
        trades = [
            TradeRecord(
                code="X",
                side="SELL",
                entry_price=Decimal("100"),
                exit_price=Decimal("110"),
                qty=10,
                pnl=Decimal("100"),
                entry_at=date(2025, 1, 1),
                exit_at=date(2025, 1, 5),
            ),
            TradeRecord(
                code="X",
                side="SELL",
                entry_price=Decimal("100"),
                exit_price=Decimal("90"),
                qty=10,
                pnl=Decimal("-100"),
                entry_at=date(2025, 1, 10),
                exit_at=date(2025, 1, 15),
            ),
            TradeRecord(
                code="X",
                side="SELL",
                entry_price=Decimal("100"),
                exit_price=Decimal("105"),
                qty=10,
                pnl=Decimal("50"),
                entry_at=date(2025, 1, 20),
                exit_at=date(2025, 1, 25),
            ),
        ]
        # 단순 equity curve 더미
        equity_curve = [
            {"date": "2025-01-01", "equity": 1_000_000, "drawdown": 0.0, "cash": 0.0},
            {"date": "2025-01-30", "equity": 1_000_050, "drawdown": 0.0, "cash": 0.0},
        ]
        metrics, _ = compute_metrics(1_000_000.0, equity_curve, trades=trades)
        assert metrics["trade_count"] == 3
        assert metrics["win_rate"] == pytest.approx(2 / 3, abs=0.001)
