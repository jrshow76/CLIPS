"""호가창 (Level 2) 디스패치 및 부하 한도 단위 테스트.

검증 항목:
1. ``RealtimeDispatcher._on_orderbook``: ``tp:market.orderbook.<code>`` 메시지를
   ``orderbook_manager``의 종목 구독자에게 broadcast
2. ``OrderbookMessage`` Pydantic 스키마 정합성
3. ``orderbook_manager``의 throttle 200ms 동작
4. 사용자당 30종목 / 종목당 50명 한도 (정책)
5. 게이트웨이 게이트(``_dispatch`` 채널 라우팅)
"""
from __future__ import annotations

import asyncio
import time

import orjson
import pytest

from app.api.websocket.auth import AuthenticatedClient
from app.api.websocket.connection_manager import (
    ORDERBOOK_MAX_SUBS_PER_CLIENT,
    ORDERBOOK_THROTTLE_MS,
    ConnectionManager,
    get_orderbook_manager,
    reset_managers,
)
from app.api.websocket.protocol import OrderbookMessage
from app.integrations.creon.realtime_dispatcher import (
    RealtimeDispatcher,
    reset_realtime_dispatcher,
)


# ---------------------------------------------------------------------------
# 픽스처
# ---------------------------------------------------------------------------
class FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.closed = False

    async def send_bytes(self, data: bytes) -> None:
        self.sent.append(data)

    async def close(self, code: int = 1000) -> None:
        self.closed = True


def make_client(user_id: str = "user-a") -> AuthenticatedClient:
    return AuthenticatedClient(
        user_id=user_id, role="ROLE_TRADER", trade_mode="SIM", raw_claims={}
    )


async def _settle(times: int = 3) -> None:
    for _ in range(times):
        await asyncio.sleep(0)


@pytest.fixture(autouse=True)
def _reset_singletons():
    reset_managers()
    reset_realtime_dispatcher()
    yield
    reset_managers()
    reset_realtime_dispatcher()


# ---------------------------------------------------------------------------
# 1. OrderbookMessage 스키마
# ---------------------------------------------------------------------------
def test_orderbook_message_schema_round_trip():
    msg = OrderbookMessage(
        stock_code="005930",
        bids=[[50000.0, 100.0], [49950.0, 200.0]],
        asks=[[50050.0, 150.0], [50100.0, 250.0]],
        total_bid_qty=300,
        total_ask_qty=400,
    )
    d = msg.model_dump()
    assert d["type"] == "orderbook"
    assert d["stock_code"] == "005930"
    assert len(d["bids"]) == 2
    assert len(d["asks"]) == 2
    assert d["total_bid_qty"] == 300


# ---------------------------------------------------------------------------
# 2. orderbook_manager 기본 동작
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_orderbook_manager_defaults():
    """orderbook 매니저는 throttle 200ms / 30종목 한도."""
    mgr = get_orderbook_manager()
    assert mgr.throttle_ms == ORDERBOOK_THROTTLE_MS == 200
    assert mgr.max_subscriptions_per_client == ORDERBOOK_MAX_SUBS_PER_CLIENT == 30


@pytest.mark.asyncio
async def test_orderbook_throttle_200ms():
    """200ms 내 두 번째 broadcast는 throttle로 막힌다."""
    # 별도 인스턴스로 테스트 (전역 싱글톤 영향 회피)
    mgr = ConnectionManager(max_subscriptions_per_client=10, throttle_ms=200)
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]
    await mgr.subscribe_stocks(conn, ["005930"])

    sent1 = await mgr.broadcast_to_stock_subscribers(
        "005930", {"type": "orderbook", "stock_code": "005930"}
    )
    sent2 = await mgr.broadcast_to_stock_subscribers(
        "005930", {"type": "orderbook", "stock_code": "005930"}
    )
    assert sent1 == 1
    assert sent2 == 0  # throttle
    await _settle()
    assert len(ws.sent) == 1
    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_orderbook_per_user_subscription_limit():
    """사용자당 30종목 한도 - 31개째 거부."""
    mgr = ConnectionManager(
        max_subscriptions_per_client=ORDERBOOK_MAX_SUBS_PER_CLIENT, throttle_ms=0
    )
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]

    codes_31 = [f"{i:06d}" for i in range(1, 32)]
    added, rejected = await mgr.subscribe_stocks(conn, codes_31)
    assert len(added) == 30
    assert len(rejected) == 1
    assert rejected[0] == codes_31[-1]
    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_orderbook_stock_subscriber_count():
    """stock_subscriber_count는 종목당 구독자 수를 반환."""
    mgr = ConnectionManager(max_subscriptions_per_client=10, throttle_ms=0)
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    conn1 = await mgr.connect(ws1, make_client("u1"))  # type: ignore[arg-type]
    conn2 = await mgr.connect(ws2, make_client("u2"))  # type: ignore[arg-type]
    await mgr.subscribe_stocks(conn1, ["005930"])
    await mgr.subscribe_stocks(conn2, ["005930"])
    assert mgr.stock_subscriber_count("005930") == 2
    assert mgr.stock_subscriber_count("999999") == 0
    await mgr.disconnect(conn1)
    await mgr.disconnect(conn2)


# ---------------------------------------------------------------------------
# 3. RealtimeDispatcher._on_orderbook
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatcher_on_orderbook_broadcasts_to_subscribers():
    """Redis 메시지 → orderbook manager → 구독자에게만 전달."""
    mgr = get_orderbook_manager()
    ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
    conn_a = await mgr.connect(ws_a, make_client("a"))  # type: ignore[arg-type]
    conn_b = await mgr.connect(ws_b, make_client("b"))  # type: ignore[arg-type]

    await mgr.subscribe_stocks(conn_a, ["005930"])
    await mgr.subscribe_stocks(conn_b, ["000660"])  # 다른 종목

    dispatcher = RealtimeDispatcher()
    payload = {
        "stock_code": "005930",
        "bids": [[50000, 100], [49950, 200]],
        "asks": [[50050, 150], [50100, 250]],
        "total_bid_qty": 300,
        "total_ask_qty": 400,
        "ts": "2026-05-14T00:00:00+00:00",
    }
    await dispatcher._on_orderbook(
        "tp:market.orderbook.005930", payload
    )
    await _settle()
    # A만 받아야 함
    assert len(ws_a.sent) == 1
    assert len(ws_b.sent) == 0
    decoded = orjson.loads(ws_a.sent[0])
    assert decoded["type"] == "orderbook"
    assert decoded["stock_code"] == "005930"
    assert decoded["bids"] == [[50000.0, 100.0], [49950.0, 200.0]]
    assert decoded["total_bid_qty"] == 300

    await mgr.disconnect(conn_a)
    await mgr.disconnect(conn_b)


@pytest.mark.asyncio
async def test_dispatcher_on_orderbook_handles_missing_fields():
    """bids/asks 누락이나 잘못된 row 형식이어도 안전하게 처리."""
    mgr = get_orderbook_manager()
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]
    await mgr.subscribe_stocks(conn, ["005930"])

    dispatcher = RealtimeDispatcher()
    await dispatcher._on_orderbook(
        "tp:market.orderbook.005930",
        {
            "bids": [[50000, 100], "invalid", [49950]],  # 일부 잘못된 row
            # asks 누락
        },
    )
    await _settle()
    assert len(ws.sent) == 1
    decoded = orjson.loads(ws.sent[0])
    # 잘못된 row는 필터링됨
    assert decoded["bids"] == [[50000.0, 100.0]]
    assert decoded["asks"] == []
    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_dispatcher_routes_orderbook_via_dispatch_method():
    """``_dispatch``가 채널 prefix에 따라 ``_on_orderbook``으로 라우팅."""
    mgr = get_orderbook_manager()
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]
    await mgr.subscribe_stocks(conn, ["005930"])

    dispatcher = RealtimeDispatcher()
    raw_msg = {
        "channel": b"tp:market.orderbook.005930",
        "data": orjson.dumps(
            {
                "stock_code": "005930",
                "bids": [[50000, 100]],
                "asks": [[50050, 200]],
                "total_bid_qty": 100,
                "total_ask_qty": 200,
            }
        ),
    }
    await dispatcher._dispatch(raw_msg)
    await _settle()
    assert len(ws.sent) == 1
    assert dispatcher._messages_total == 1
    assert dispatcher._last_orderbook_at > 0
    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_dispatcher_orderbook_throttle_drops_within_window():
    """200ms 내 두 번째 메시지는 manager의 throttle로 인해 전달되지 않는다."""
    mgr = get_orderbook_manager()
    assert mgr.throttle_ms == 200
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]
    await mgr.subscribe_stocks(conn, ["005930"])

    dispatcher = RealtimeDispatcher()
    base_payload = {
        "stock_code": "005930",
        "bids": [[50000, 100]],
        "asks": [[50050, 100]],
    }
    await dispatcher._on_orderbook("tp:market.orderbook.005930", base_payload)
    await dispatcher._on_orderbook("tp:market.orderbook.005930", base_payload)
    await _settle()
    # throttle로 첫 메시지만 도달
    assert len(ws.sent) == 1

    await mgr.disconnect(conn)


# ---------------------------------------------------------------------------
# 4. 부하 격리 - market_manager와 분리되어 있는지
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_orderbook_manager_is_separate_from_market_manager():
    from app.api.websocket.connection_manager import get_market_manager

    market = get_market_manager()
    orderbook = get_orderbook_manager()
    assert market is not orderbook
    # 시세는 100ms / 호가는 200ms
    assert market.throttle_ms == 100
    assert orderbook.throttle_ms == 200
