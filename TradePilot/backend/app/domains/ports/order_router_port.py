"""OrderRouterPort: 주문 라우터 추상 인터페이스.

구현체:
- `app.integrations.simulator.sim_order_router.SimOrderRouter`
- `app.integrations.creon.live_order_router.LiveOrderRouter`
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class OrderRequest:
    """주문 요청 DTO (라우터 입력)."""

    order_id: int  # DB 주문 PK (서비스 계층에서 미리 생성)
    user_id: int
    stock_code: str
    side: str  # BUY | SELL
    order_type: str  # MARKET | LIMIT
    qty: Decimal
    price: Decimal | None = None
    trade_mode: str = "SIM"
    idempotency_key: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderResult:
    """주문 처리 결과 DTO."""

    accepted: bool
    status: str  # NEW | ACCEPTED | FILLED | REJECTED | CANCELED ...
    broker_order_no: str | None = None
    filled_qty: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    fee: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    slippage: Decimal | None = None
    filled_at: datetime | None = None
    reject_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class OrderRouterPort(ABC):
    """주문 라우터 포트.

    submit/cancel은 비동기. 시장가 SIM은 즉시 체결, LIVE는 게이트웨이로 전달.
    """

    @abstractmethod
    async def submit_order(self, request: OrderRequest) -> OrderResult:
        """주문 발주."""

    @abstractmethod
    async def cancel_order(
        self,
        order_id: int,
        broker_order_no: str | None,
        stock_code: str,
        *,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> OrderResult:
        """주문 취소.

        SEC-003(GATE-1) 보강:
        - ``timeout_sec``: 호출별 타임아웃 오버라이드 (None이면 클라이언트 기본).
          Kill Switch는 2.0초로 강제하여 SLA 보장.
        - ``idempotency_key``: 중복 발주 방지를 위한 X-Idempotency-Key 값.
        """

    @abstractmethod
    async def get_order_status(
        self, order_id: int, broker_order_no: str | None
    ) -> OrderResult:
        """주문 상태 조회."""
