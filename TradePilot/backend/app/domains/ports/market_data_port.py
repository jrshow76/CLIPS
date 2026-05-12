"""MarketDataPort: 시세 데이터 추상 인터페이스."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass
class QuoteSnapshot:
    """현재가 스냅샷."""

    code: str
    price: Decimal
    change: Decimal | None = None
    change_pct: Decimal | None = None
    volume: int = 0
    ts: datetime | None = None
    source: str = "creon"


@dataclass
class OrderbookSnapshot:
    """호가 10단계."""

    code: str
    bids: list[tuple[Decimal, int]] = field(default_factory=list)  # (price, qty)
    asks: list[tuple[Decimal, int]] = field(default_factory=list)
    ts: datetime | None = None


@dataclass
class CandleBar:
    """OHLCV 캔들."""

    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    interval: str = "D"


class MarketDataPort(ABC):
    """시세 데이터 포트."""

    @abstractmethod
    async def get_snapshot(self, code: str) -> QuoteSnapshot:
        """현재가 스냅샷."""

    @abstractmethod
    async def get_orderbook(self, code: str) -> OrderbookSnapshot:
        """호가."""

    @abstractmethod
    async def get_history(
        self,
        code: str,
        interval: str = "D",
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[CandleBar]:
        """과거 캔들 조회."""

    @abstractmethod
    async def subscribe_ticks(self, codes: list[str]) -> AsyncIterator[QuoteSnapshot]:
        """실시간 시세 구독 (async generator)."""
