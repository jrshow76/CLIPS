"""백테스트 전략 플러그인."""
from app.services.backtest_engine.strategies.base import Strategy
from app.services.backtest_engine.strategies.registry import get_strategy, register_strategy

# 부작용 import: 각 전략 모듈이 import 되면서 registry 에 등록되도록 한다.
from app.services.backtest_engine.strategies import (  # noqa: F401
    bollinger_breakout,
    composite,
    golden_cross,
    macd_cross,
    rsi_reversal,
)

__all__ = ["Strategy", "get_strategy", "register_strategy"]
