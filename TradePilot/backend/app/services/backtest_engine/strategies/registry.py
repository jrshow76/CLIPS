"""전략 식별자 → 클래스 매핑 레지스트리."""
from __future__ import annotations

from typing import Type

from app.services.backtest_engine.strategies.base import Strategy


_REGISTRY: dict[str, Type[Strategy]] = {}


def register_strategy(name: str, cls: Type[Strategy]) -> None:
    """전략 클래스를 등록한다."""
    _REGISTRY[name] = cls


def get_strategy(name: str) -> Type[Strategy] | None:
    return _REGISTRY.get(name)


def list_strategies() -> list[str]:
    return sorted(_REGISTRY.keys())
