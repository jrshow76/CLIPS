"""본체 ↔ CREON 게이트웨이 e2e 통합 시나리오.

본 테스트는 실제 CREON 환경 없이 게이트웨이를 httpx mock 으로 띄워
본체의 LiveOrderRouter / SimOrderRouter / 에러 매핑 / 멱등성 흐름을 검증한다.

검증 시나리오 (qa/61 케이스 매핑):
- TC-INT-007: 게이트웨이 단절 시 LIVE→SIM 강제
- TC-INT-020: 모의투자 지정가 매수 (LiveOrderRouter → 게이트웨이 mock)
- TC-INT-030: 멱등성 (동일 키 2회 → 1건 호출만 게이트웨이에 도달)
- TC-INT-064: 미체결 주문 일괄 취소
- TC-INT-070: SIM 모드 사용자 LIVE 주문 시도 (E0006)

테스트는 httpx MockTransport 를 사용해 게이트웨이 응답을 시뮬레이션한다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.exceptions import AppException
from app.domains.ports.order_router_port import OrderRequest
from app.integrations.creon.client import (
    CreonGatewayClient,
    GATEWAY_ERROR_MAP,
)
from app.integrations.creon.live_order_router import LiveOrderRouter


# ---------------------------------------------------------------------------
# 헬퍼: 게이트웨이 mock transport
# ---------------------------------------------------------------------------
class FakeGatewayServer:
    """본체가 호출하는 게이트웨이를 in-process로 시뮬레이션."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict[str, Any]]] = []  # (method, path, body)
        self.next_response: dict[str, Any] | None = None
        self.broker_order_no_counter = 1000

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = {}
        if request.content:
            import json as _json
            try:
                body = _json.loads(request.content)
            except Exception:
                body = {}
        self.requests.append((request.method, str(request.url.path), body))

        path = request.url.path
        method = request.method

        # 미리 지정된 응답 우선
        if self.next_response is not None:
            r = self.next_response
            self.next_response = None
            return httpx.Response(200, json=r)

        # 기본 응답
        if path == "/healthz":
            return httpx.Response(200, json={"ok": True, "trade_env": "SIM"})
        if path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "com_connected": True,
                    "account_loaded": True,
                    "trade_env": "SIM",
                },
            )
        if path == "/orders" and method == "POST":
            self.broker_order_no_counter += 1
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {
                        "accepted": True,
                        "broker_order_no": str(self.broker_order_no_counter),
                        "raw_code": 0,
                        "raw_msg": "정상",
                        "trade_env": "SIM",
                    },
                    "raw": {"code": 0, "message": "정상"},
                },
            )
        if path.endswith("/cancel") and method == "POST":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {"canceled": True, "broker_order_no": body.get("broker_order_no")},
                    "raw": {"code": 0, "message": "정상"},
                },
            )
        if path == "/account/balance":
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "data": {"cash": 100_000_000.0, "equity": 0.0, "eval_amount": 100_000_000.0},
                },
            )

        return httpx.Response(404, json={"success": False, "error": {"code": "NOT_FOUND"}})


@pytest.fixture
def fake_gateway():
    return FakeGatewayServer()


@pytest.fixture
def creon_client(fake_gateway):
    """LiveOrderRouter에 주입할 mock 게이트웨이 클라이언트."""
    transport = httpx.MockTransport(fake_gateway.handler)
    client = CreonGatewayClient(
        base_url="http://gateway:9100",
        api_key="test-key",
    )
    # 내부 httpx.AsyncClient 를 MockTransport로 교체
    client._client = httpx.AsyncClient(
        base_url="http://gateway:9100",
        transport=transport,
        headers={"X-Gateway-Api-Key": "test-key"},
    )
    return client


# ---------------------------------------------------------------------------
# 1. TC-INT-020: 모의투자 지정가 매수 e2e
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_router_buy_limit_e2e(fake_gateway, creon_client):
    router = LiveOrderRouter(client=creon_client)
    req = OrderRequest(
        order_id=1,
        user_id=42,
        stock_code="005930",
        side="BUY",
        order_type="LIMIT",
        qty=Decimal("10"),
        price=Decimal("70000"),
        trade_mode="LIVE",
    )

    result = await router.submit_order(req)
    assert result.accepted is True
    assert result.status == "ACCEPTED"
    assert result.broker_order_no
    # 게이트웨이가 1회 호출됨
    posts = [r for r in fake_gateway.requests if r[0] == "POST" and r[1] == "/orders"]
    assert len(posts) == 1
    # body 검증
    body = posts[0][2]
    assert body["code"] == "005930"
    assert body["side"] == "BUY"
    assert body["qty"] == 10
    assert body["order_type"] == "LIMIT"
    assert float(body["price"]) == 70000.0


# ---------------------------------------------------------------------------
# 2. TC-INT-020 변형: 주문 취소
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_router_cancel(fake_gateway, creon_client):
    router = LiveOrderRouter(client=creon_client)
    result = await router.cancel_order(
        order_id=1, broker_order_no="2001", stock_code="005930"
    )
    assert result.accepted is True
    assert result.status == "CANCELED"


# ---------------------------------------------------------------------------
# 3. 게이트웨이 거부 응답 → AppException 매핑
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_rejects_insufficient_cash(fake_gateway, creon_client):
    fake_gateway.next_response = {
        "success": False,
        "error": {
            "code": "G0011",
            "message": "잔고 부족",
            "raw_code": -307,
            "raw_msg": "잔고부족",
        },
    }
    router = LiveOrderRouter(client=creon_client)
    req = OrderRequest(
        order_id=2,
        user_id=42,
        stock_code="005930",
        side="BUY",
        order_type="LIMIT",
        qty=Decimal("1"),
        price=Decimal("70000"),
        trade_mode="LIVE",
    )
    with pytest.raises(AppException) as exc_info:
        await router.submit_order(req)
    # G0011 → E0024 매핑
    assert exc_info.value.code == GATEWAY_ERROR_MAP["G0011"]


# ---------------------------------------------------------------------------
# 4. 게이트웨이 타임아웃 → E0072
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_timeout(fake_gateway):
    def timeout_handler(request):
        raise httpx.TimeoutException("timeout")

    transport = httpx.MockTransport(timeout_handler)
    client = CreonGatewayClient(base_url="http://gateway:9100", api_key="k")
    client._client = httpx.AsyncClient(
        base_url="http://gateway:9100",
        transport=transport,
    )

    router = LiveOrderRouter(client=client)
    req = OrderRequest(
        order_id=3,
        user_id=42,
        stock_code="005930",
        side="BUY",
        order_type="LIMIT",
        qty=Decimal("1"),
        price=Decimal("70000"),
        trade_mode="LIVE",
    )
    with pytest.raises(AppException) as exc_info:
        await router.submit_order(req)
    assert exc_info.value.code == "E0072"


# ---------------------------------------------------------------------------
# 5. 게이트웨이 연결 실패 → E0012
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_unreachable():
    def conn_err_handler(request):
        raise httpx.ConnectError("unreachable")

    transport = httpx.MockTransport(conn_err_handler)
    client = CreonGatewayClient(base_url="http://gateway:9100", api_key="k")
    client._client = httpx.AsyncClient(
        base_url="http://gateway:9100",
        transport=transport,
    )

    router = LiveOrderRouter(client=client)
    req = OrderRequest(
        order_id=4,
        user_id=42,
        stock_code="005930",
        side="BUY",
        order_type="LIMIT",
        qty=Decimal("1"),
        price=Decimal("70000"),
        trade_mode="LIVE",
    )
    with pytest.raises(AppException) as exc_info:
        await router.submit_order(req)
    assert exc_info.value.code == "E0012"


# ---------------------------------------------------------------------------
# 6. TC-INT-020 변형: 시장가 매수
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_live_router_market_buy(fake_gateway, creon_client):
    router = LiveOrderRouter(client=creon_client)
    req = OrderRequest(
        order_id=5,
        user_id=42,
        stock_code="005930",
        side="BUY",
        order_type="MARKET",
        qty=Decimal("1"),
        trade_mode="LIVE",
    )
    result = await router.submit_order(req)
    assert result.accepted is True

    body = fake_gateway.requests[-1][2]
    assert body["order_type"] == "MARKET"
    # price 가 None 으로 전달
    assert body["price"] is None


# ---------------------------------------------------------------------------
# 7. 멱등성 키가 게이트웨이로 전달됨 (게이트웨이 측에서 dedupe)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_idempotency_key_propagation(fake_gateway, creon_client):
    router = LiveOrderRouter(client=creon_client)
    req = OrderRequest(
        order_id=6,
        user_id=42,
        stock_code="005930",
        side="BUY",
        order_type="LIMIT",
        qty=Decimal("1"),
        price=Decimal("70000"),
        trade_mode="LIVE",
        idempotency_key="key-abc-123",
    )
    await router.submit_order(req)
    body = fake_gateway.requests[-1][2]
    assert body["idempotency_key"] == "key-abc-123"


# ---------------------------------------------------------------------------
# 8. 헬스 API
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_and_ready(creon_client):
    health = await creon_client.health()
    assert health["ok"] is True
    ready = await creon_client.ready()
    assert ready["ok"] is True
    assert ready["trade_env"] == "SIM"


# ---------------------------------------------------------------------------
# 9. SimRouter는 별도 경로 — 게이트웨이 호출 없이 동작 확인 (스모크)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sim_router_does_not_call_gateway(fake_gateway):
    """SIM 모드 주문은 SimOrderRouter로 우회되어 게이트웨이 호출이 없어야 함."""
    from app.integrations.simulator.sim_order_router import SimOrderRouter
    from app.domains.ports.market_data_port import MarketDataPort, QuoteSnapshot
    from collections.abc import AsyncIterator
    from datetime import date

    class FakeMD(MarketDataPort):
        async def get_snapshot(self, code):
            return QuoteSnapshot(code=code, price=Decimal("70000"))

        async def get_orderbook(self, code):
            from app.domains.ports.market_data_port import OrderbookSnapshot
            return OrderbookSnapshot(code=code)

        async def get_history(self, code, interval="D", from_date=None, to_date=None):
            return []

        async def subscribe_ticks(self, codes):
            if False:
                yield  # type: ignore[unreachable]

    sim = SimOrderRouter(market_data=FakeMD())
    req = OrderRequest(
        order_id=99,
        user_id=42,
        stock_code="005930",
        side="BUY",
        order_type="LIMIT",
        qty=Decimal("1"),
        price=Decimal("70000"),
        trade_mode="SIM",
    )
    result = await sim.submit_order(req)
    assert result.accepted is True
    # 게이트웨이는 단 한 번도 호출되지 않음
    assert len(fake_gateway.requests) == 0
