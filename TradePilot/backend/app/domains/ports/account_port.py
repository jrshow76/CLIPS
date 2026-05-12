"""AccountPort: 계좌/잔고/포지션 추상 인터페이스."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class AccountBalance:
    """잔고 스냅샷."""

    cash: Decimal
    equity: Decimal
    total_value: Decimal
    trade_mode: str = "SIM"


@dataclass
class PositionSnapshot:
    """보유 종목 스냅샷."""

    code: str
    qty: Decimal
    avg_price: Decimal
    current_price: Decimal | None = None
    eval_pnl: Decimal | None = None
    trade_mode: str = "SIM"


@dataclass
class ExecutionEvent:
    """체결 이벤트."""

    order_id: int | None
    broker_order_no: str | None
    code: str
    side: str
    qty: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    ts: datetime | None = None


class AccountPort(ABC):
    """계좌 포트."""

    @abstractmethod
    async def get_balance(self, user_id: int, trade_mode: str) -> AccountBalance:
        """예수금/평가금액."""

    @abstractmethod
    async def get_positions(self, user_id: int, trade_mode: str) -> list[PositionSnapshot]:
        """보유 종목 리스트."""

    @abstractmethod
    async def get_executions(
        self, user_id: int, trade_mode: str, since: datetime | None = None
    ) -> list[ExecutionEvent]:
        """체결 이력."""
