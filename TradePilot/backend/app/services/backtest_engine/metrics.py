"""백테스트 결과 메트릭 계산.

산출 항목:
- cumulative_return: 누적 수익률
- annualized_return (CAGR): 연환산 수익률
- volatility: 일간 수익률 표준편차의 연환산
- sharpe: 샤프 지수 (rf=0)
- sortino: 소르티노 지수 (downside std)
- mdd: 최대 낙폭 (음수)
- recovery_period_days: MDD 회복 기간 (영업일 수)
- calmar: CAGR / |MDD|
- win_rate: 승률 (수익 거래 / 전체 거래)
- profit_factor: 총 이익 / |총 손실|
- avg_holding_days: 평균 보유일
- trade_count: 총 청산 거래 수
- monthly_returns: {"YYYY-MM": float}
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from app.services.backtest_engine.config import TradeRecord


TRADING_DAYS_PER_YEAR = 252


def compute_metrics(
    initial_capital: float,
    equity_curve: list[dict[str, Any]],
    trades: list[TradeRecord],
) -> tuple[dict[str, Any], dict[str, float]]:
    """메트릭 + 월별 수익률 산출.

    Returns:
        (metrics, monthly_returns)
    """
    if not equity_curve:
        return _empty_metrics(initial_capital), {}

    df = pd.DataFrame(equity_curve)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    final_equity = float(df["equity"].iloc[-1])
    cumulative_return = final_equity / initial_capital - 1.0

    days = len(df)
    years = days / TRADING_DAYS_PER_YEAR if days > 0 else 0.0
    if years > 0 and final_equity > 0:
        cagr = (final_equity / initial_capital) ** (1.0 / years) - 1.0
    else:
        cagr = 0.0

    daily_ret = df["equity"].pct_change().dropna()
    if len(daily_ret) > 1:
        volatility = float(daily_ret.std(ddof=0) * math.sqrt(TRADING_DAYS_PER_YEAR))
        mean_ret = float(daily_ret.mean() * TRADING_DAYS_PER_YEAR)
        sharpe = mean_ret / volatility if volatility > 0 else 0.0
        downside = daily_ret[daily_ret < 0]
        downside_std = float(downside.std(ddof=0) * math.sqrt(TRADING_DAYS_PER_YEAR)) if len(downside) > 1 else 0.0
        sortino = mean_ret / downside_std if downside_std > 0 else 0.0
    else:
        volatility = 0.0
        sharpe = 0.0
        sortino = 0.0

    # MDD: drawdown 컬럼 최솟값
    mdd = float(df["drawdown"].min()) if "drawdown" in df.columns else _calc_mdd(df["equity"])
    recovery_days = _recovery_days(df["equity"])

    calmar = (cagr / abs(mdd)) if mdd < 0 else 0.0

    # 거래 통계
    closed = [t for t in trades if t.pnl is not None]
    trade_count = len(closed)
    wins = [t for t in closed if (t.pnl or Decimal("0")) > 0]
    losses = [t for t in closed if (t.pnl or Decimal("0")) <= 0]
    win_rate = (len(wins) / trade_count) if trade_count > 0 else 0.0
    gross_profit = sum(float(t.pnl) for t in wins) if wins else 0.0
    gross_loss = abs(sum(float(t.pnl) for t in losses)) if losses else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)

    holding_days = []
    for t in closed:
        if t.entry_at and t.exit_at:
            holding_days.append((t.exit_at - t.entry_at).days)
    avg_hold = float(np.mean(holding_days)) if holding_days else 0.0

    # 월별 수익률
    monthly = df["equity"].resample("ME").last().pct_change().dropna()
    monthly_returns = {ts.strftime("%Y-%m"): float(round(v, 6)) for ts, v in monthly.items()}

    metrics: dict[str, Any] = {
        "cumulative_return": round(cumulative_return, 6),
        "annualized_return": round(cagr, 6),
        "volatility": round(volatility, 6),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "mdd": round(mdd, 6),
        "recovery_period_days": int(recovery_days) if recovery_days is not None else None,
        "calmar": round(calmar, 4) if math.isfinite(calmar) else None,
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4) if math.isfinite(profit_factor) else None,
        "avg_holding_days": round(avg_hold, 2),
        "trade_count": trade_count,
        "final_equity": round(final_equity, 2),
    }
    return metrics, monthly_returns


def _calc_mdd(equity: pd.Series) -> float:
    if len(equity) == 0:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def _recovery_days(equity: pd.Series) -> int | None:
    """MDD 발생 후 이전 고점을 다시 회복하기까지의 영업일 수.

    회복하지 못한 경우 None.
    """
    if equity.empty:
        return None
    peak = equity.cummax()
    dd = equity / peak - 1.0
    if dd.min() == 0:
        return 0
    trough_idx = dd.idxmin()
    peak_value_at_trough = peak.loc[trough_idx]
    after = equity.loc[trough_idx:]
    recovered = after[after >= peak_value_at_trough]
    if recovered.empty:
        return None
    recovery_idx = recovered.index[0]
    return int((recovery_idx - trough_idx).days)


def _empty_metrics(initial_capital: float) -> dict[str, Any]:
    return {
        "cumulative_return": 0.0,
        "annualized_return": 0.0,
        "volatility": 0.0,
        "sharpe": 0.0,
        "sortino": 0.0,
        "mdd": 0.0,
        "recovery_period_days": None,
        "calmar": None,
        "win_rate": 0.0,
        "profit_factor": None,
        "avg_holding_days": 0.0,
        "trade_count": 0,
        "final_equity": initial_capital,
    }
