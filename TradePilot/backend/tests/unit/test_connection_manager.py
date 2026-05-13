"""ConnectionManager 단위 테스트.

- 구독/해제 정확성
- 종목별 broadcast 라우팅 (구독자에게만 전송)
- throttle 동작 (100ms 간격 보장)
- 종목 50개 한도 초과 시 reject
- 큐 cap 도달 시 oldest drop
- 사용자별 send_to_user
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.api.websocket.auth import AuthenticatedClient
from app.api.websocket.connection_manager import ConnectionManager


class FakeWebSocket:
    """ConnectionManager가 호출하는 send_bytes / close만 흉내."""

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
    """sender 코루틴이 큐를 드레인할 시간 확보."""
    for _ in range(times):
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe_basic():
    mgr = ConnectionManager(max_subscriptions_per_client=10, throttle_ms=0)
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]

    added, rejected = await mgr.subscribe_stocks(conn, ["005930", "000660"])
    assert added == ["005930", "000660"]
    assert rejected == []
    assert conn.subscribed_codes == {"005930", "000660"}

    removed = await mgr.unsubscribe_stocks(conn, ["005930"])
    assert removed == ["005930"]
    assert conn.subscribed_codes == {"000660"}

    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_subscribe_dedup_and_limit():
    mgr = ConnectionManager(max_subscriptions_per_client=3, throttle_ms=0)
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]

    added1, _ = await mgr.subscribe_stocks(conn, ["005930", "005930", "000660"])
    assert sorted(added1) == ["000660", "005930"]

    # 한도 초과
    added2, rejected = await mgr.subscribe_stocks(
        conn, ["035420", "035720", "068270"]
    )
    assert sorted(added2) == ["035420"]
    assert sorted(rejected) == ["035720", "068270"]
    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_broadcast_routes_only_to_subscribers():
    mgr = ConnectionManager(max_subscriptions_per_client=10, throttle_ms=0)
    ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
    conn_a = await mgr.connect(ws_a, make_client("a"))  # type: ignore[arg-type]
    conn_b = await mgr.connect(ws_b, make_client("b"))  # type: ignore[arg-type]

    await mgr.subscribe_stocks(conn_a, ["005930"])
    await mgr.subscribe_stocks(conn_b, ["000660"])

    sent = await mgr.broadcast_to_stock_subscribers(
        "005930", {"type": "tick", "stock_code": "005930", "price": 71000}
    )
    assert sent == 1
    await _settle()
    assert len(ws_a.sent) == 1
    assert len(ws_b.sent) == 0

    await mgr.disconnect(conn_a)
    await mgr.disconnect(conn_b)


@pytest.mark.asyncio
async def test_broadcast_throttle_drops_within_window():
    mgr = ConnectionManager(max_subscriptions_per_client=10, throttle_ms=200)
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]
    await mgr.subscribe_stocks(conn, ["005930"])

    # 첫 broadcast: 통과
    sent1 = await mgr.broadcast_to_stock_subscribers(
        "005930", {"type": "tick", "stock_code": "005930", "price": 70000}
    )
    # 즉시 재전송: throttle로 막힘
    sent2 = await mgr.broadcast_to_stock_subscribers(
        "005930", {"type": "tick", "stock_code": "005930", "price": 70100}
    )
    assert sent1 == 1
    assert sent2 == 0
    await _settle()
    assert len(ws.sent) == 1

    # throttle 윈도우 경과 후 통과
    await asyncio.sleep(0.25)
    sent3 = await mgr.broadcast_to_stock_subscribers(
        "005930", {"type": "tick", "stock_code": "005930", "price": 70200}
    )
    assert sent3 == 1
    await _settle()
    assert len(ws.sent) == 2

    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_send_to_user_targets_all_user_connections():
    mgr = ConnectionManager(max_subscriptions_per_client=0, throttle_ms=0)
    ws1, ws2, ws_other = FakeWebSocket(), FakeWebSocket(), FakeWebSocket()
    conn1 = await mgr.connect(ws1, make_client("u1"))  # type: ignore[arg-type]
    conn2 = await mgr.connect(ws2, make_client("u1"))  # type: ignore[arg-type]
    conn3 = await mgr.connect(ws_other, make_client("u2"))  # type: ignore[arg-type]

    sent = await mgr.send_to_user("u1", {"type": "execution", "qty": 10})
    assert sent == 2
    await _settle()
    assert len(ws1.sent) == 1
    assert len(ws2.sent) == 1
    assert len(ws_other.sent) == 0

    await mgr.disconnect(conn1)
    await mgr.disconnect(conn2)
    await mgr.disconnect(conn3)


@pytest.mark.asyncio
async def test_queue_cap_drops_oldest():
    mgr = ConnectionManager(max_subscriptions_per_client=10, throttle_ms=0, max_queue_size=3)
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client())  # type: ignore[arg-type]

    # sender가 즉시 드레인되지 않도록 send_bytes를 잠시 블록
    block = asyncio.Event()

    async def slow_send(data: bytes) -> None:
        await block.wait()
        ws.sent.append(data)

    ws.send_bytes = slow_send  # type: ignore[assignment,method-assign]

    for i in range(6):
        await mgr.send_to_connection(conn, {"i": i})

    # 큐는 max 3개만 보유 (가장 최근 3건). drop_count = 3
    assert len(conn.send_queue) <= 3
    assert conn.drop_count == 3

    block.set()
    await mgr.disconnect(conn)


@pytest.mark.asyncio
async def test_disconnect_is_idempotent_and_cleans_state():
    mgr = ConnectionManager(max_subscriptions_per_client=10, throttle_ms=0)
    ws = FakeWebSocket()
    conn = await mgr.connect(ws, make_client("u1"))  # type: ignore[arg-type]
    await mgr.subscribe_stocks(conn, ["005930"])

    assert mgr.stats()["connections"] == 1
    await mgr.disconnect(conn)
    await mgr.disconnect(conn)  # 중복 호출 안전
    stats = mgr.stats()
    assert stats["connections"] == 0
    assert stats["users"] == 0
    assert stats["subscribed_stocks"] == 0
