"""TradePilot 백테스트 엔진.

외부에 노출하는 API:
    - run_backtest(config, db, progress_cb)
    - BacktestConfig
    - BacktestResult
    - TradeRecord
"""
from app.services.backtest_engine.config import (
    BacktestConfig,
    BacktestResult,
    TradeRecord,
)
from app.services.backtest_engine.runner import run_backtest

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "TradeRecord",
    "run_backtest",
]
