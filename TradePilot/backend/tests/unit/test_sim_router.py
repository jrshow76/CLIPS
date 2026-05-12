"""SimOrderRouter 단위 테스트.

MarketDataPort를 모킹하여 슬리피지/수수료/세금 계산을 검증한다.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domains.ports.market_data_port import (
    CandleBar,
    MarketDataPort,
    OrderbookSnapshot,
    QuoteSnapshot,
)
from app.domains.ports.order_router_port import OrderRequest
from app.integrations.simulator.sim_order_router import (
    SIM_FEE_RATE,
    SIM_SLIPPAGE_RATE,
    SIM_TAX_RATE_SELL,
    SimOrderRouter,
)


class FakeMarketData(MarketDataPort):
    """현재가 고정 시세 어댑터."""

    def __init__(self, price: Decimal = Decimal("70000")) -> None:
        self._price = price

    async def get_snapshot(self, code: str) -> QuoteSnapshot:
        return QuoteSnapshot(code=code, price=self._price)

    async def get_orderbook(self, code: str) -> OrderbookSnapshot:
        return OrderbookSnapshot(code=code)

    async def get_history(
        self, code: str, interval: str = "D", from_date: date | None = None, to_date: date | None = None
    ) -> list[CandleBar]:
        return []

    async def subscribe_ticks(self, codes: list[str]) -> AsyncIterator[QuoteSnapshot]:
        if False:
            yield  # type: ignore[unreachable]


@pytest.fixture
def router() -> SimOrderRouter:
    return SimOrderRouter(market_data=FakeMarketData(), enable_random_delay=False)


@pytest.mark.unit
async def test_market_buy_slippage_up(router: SimOrderRouter) -> None:
    """시장가 매수는 +슬리피지가 적용된 체결가를 갖는다."""
    req = OrderRequest(
        order_id=1, user_id=1, stock_code="005930", side="BUY",
        order_type="MARKET", qty=Decimal("10"), trade_mode="SIM",
    )
    result = await router.submit_order(req)
    assert result.accepted
    assert result.status == "FILLED"
    expected_price = Decimal("70000") * (Decimal("1") + SIM_SLIPPAGE_RATE)
    assert result.avg_fill_price == expected_price.quantize(Decimal("0.01"))
    # 수수료 = 가격 * qty * 0.015%
    expected_fee = (expected_price * Decimal("10") * SIM_FEE_RATE).quantize(Decimal("0.01"))
    assert result.fee == expected_fee
    assert result.tax == Decimal("0.00")  # 매수는 세금 없음


@pytest.mark.unit
async def test_market_sell_slippage_down_and_tax(router: SimOrderRouter) -> None:
    """시장가 매도는 -슬리피지 + 거래세 적용."""
    req = OrderRequest(
        order_id=2, user_id=1, stock_code="005930", side="SELL",
        order_type="MARKET", qty=Decimal("5"), trade_mode="SIM",
    )
    result = await router.submit_order(req)
    assert result.status == "FILLED"
    expected_price = Decimal("70000") * (Decimal("1") - SIM_SLIPPAGE_RATE)
    assert result.avg_fill_price == expected_price.quantize(Decimal("0.01"))
    expected_tax = (expected_price * Decimal("5") * SIM_TAX_RATE_SELL).quantize(Decimal("0.01"))
    assert result.tax == expected_tax


@pytest.mark.unit
async def test_limit_buy_below_market_stays_new(router: SimOrderRouter) -> None:
    """매수 지정가가 현재가보다 낮으면 미체결(NEW)."""
    req = OrderRequest(
        order_id=3, user_id=1, stock_code="005930", side="BUY",
        order_type="LIMIT", qty=Decimal("1"), price=Decimal("68000"), trade_mode="SIM",
    )
    result = await router.submit_order(req)
    assert result.status == "NEW"
    assert result.filled_qty == Decimal("0")


@pytest.mark.unit
async def test_cancel_always_succeeds_in_sim(router: SimOrderRouter) -> None:
    result = await router.cancel_order(order_id=1, broker_order_no=None, stock_code="005930")
    assert result.accepted
    assert result.status == "CANCELED"
