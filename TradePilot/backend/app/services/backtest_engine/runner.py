"""백테스트 엔진 진입점.

Phase:
1) 데이터 로드 (10%)
2) 지표 사전 계산 (30%)
3) 시그널 생성 + 이벤트 드리븐 시뮬레이션 (80%)
4) 메트릭 산출 (100%)
"""
from __future__ import annotations

from typing import Callable

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.backtest_engine.config import BacktestConfig, BacktestResult
from app.services.backtest_engine.data_loader import load_daily_prices
from app.services.backtest_engine.executor import BacktestExecutor
from app.services.backtest_engine.indicators import attach_indicators
from app.services.backtest_engine.metrics import compute_metrics
from app.services.backtest_engine.strategies import get_strategy

log = structlog.get_logger(__name__)


async def run_backtest(
    config: BacktestConfig,
    db: AsyncSession,
    progress_cb: Callable[[int], None] | None = None,
) -> BacktestResult:
    """백테스트 실행 진입점.

    Args:
        config: 입력
        db: AsyncSession (price_daily 조회용)
        progress_cb: 진행률 콜백 (0~100)
    """
    _notify(progress_cb, 5)

    # 1) 데이터 로드
    frames = await load_daily_prices(
        db, config.universe, config.period_from, config.period_to
    )
    if not frames:
        log.warning("backtest_no_data", universe=config.universe)
        return _empty_result(config)
    _notify(progress_cb, 10)

    # 2) 지표 부착 (vectorized)
    enriched: dict = {}
    for code, df in frames.items():
        if df.empty:
            continue
        enriched[code] = attach_indicators(df)
    _notify(progress_cb, 30)

    # 3) 전략 시그널 생성
    strategy_cls = get_strategy(config.strategy_type)
    if strategy_cls is None:
        raise ValueError(f"Unknown strategy_type: {config.strategy_type}")
    strategy = strategy_cls(params=config.strategy_params)
    signals: dict = {}
    for code, df in enriched.items():
        try:
            signals[code] = strategy.generate_signals(df)
        except Exception as e:
            log.warning("backtest_signal_failed", code=code, error=str(e))
            continue
    _notify(progress_cb, 35)

    # 4) 이벤트 드리븐 시뮬레이션
    executor = BacktestExecutor(
        config=config,
        frames=enriched,
        signals=signals,
        progress_cb=progress_cb,
    )
    equity_curve = executor.run()
    _notify(progress_cb, 90)

    # 5) 메트릭
    metrics, monthly_returns = compute_metrics(
        initial_capital=float(config.initial_capital),
        equity_curve=equity_curve,
        trades=executor.portfolio.closed_trades,
    )
    _notify(progress_cb, 100)

    summary = {
        "engine": "tradepilot-backtest-v1",
        "strategy_type": config.strategy_type,
        "universe_size": len(config.universe),
        "trading_days": len(equity_curve),
        "fee_rate": float(config.fee_rate),
        "slippage": float(config.slippage),
        "sell_tax": float(config.sell_tax),
        "max_positions": config.max_positions,
        "execution_lag": config.execution_lag,
        "total_fee_paid": round(executor.portfolio.total_fee_paid, 2),
        "total_tax_paid": round(executor.portfolio.total_tax_paid, 2),
    }

    return BacktestResult(
        metrics=metrics,
        equity_curve=equity_curve,
        trades=executor.portfolio.closed_trades,
        monthly_returns=monthly_returns,
        summary=summary,
    )


def _notify(cb: Callable[[int], None] | None, pct: int) -> None:
    if cb is not None:
        try:
            cb(pct)
        except Exception:  # pragma: no cover - 진행률 콜백 예외는 흐름과 무관
            pass


def _empty_result(config: BacktestConfig) -> BacktestResult:
    return BacktestResult(
        metrics={
            "cumulative_return": 0.0,
            "annualized_return": 0.0,
            "mdd": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "trade_count": 0,
            "final_equity": float(config.initial_capital),
        },
        equity_curve=[],
        trades=[],
        monthly_returns={},
        summary={"engine": "tradepilot-backtest-v1", "note": "no data"},
    )
