"""게이트웨이 호가창 (StockJpBid) 단위 테스트.

검증 항목:
- ``publish_orderbook``: 채널 형식, 페이로드 정합성, 합산 잔량 자동 계산
- ``MockCreonAdapter.get_orderbook``: 10단계 매수/매도 호가 deterministic
- ``MockOrderbookWorker``: 1회 emit 시 Redis로 발행되는지
- REST ``/market/orderbook/{code}``: 어댑터 ``get_orderbook`` 사용 + envelope
"""
from __future__ import annotations

import asyncio

import orjson
import pytest

from creon_gateway import event_publisher
from creon_gateway.creon_adapter import (
    MockCreonAdapter,
    OrderbookSnapshot,
    _calc_tick_size,
    get_adapter,
)


# ---------------------------------------------------------------------------
# 1. publish_orderbook 단위 테스트
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_publish_orderbook_basic(fake_redis):
    """채널/페이로드 형식 정합성."""
    event_publisher._redis = fake_redis  # type: ignore[assignment]

    bids = [(50000.0, 100), (49950.0, 200), (49900.0, 300)]
    asks = [(50050.0, 150), (50100.0, 250), (50150.0, 350)]
    await event_publisher.publish_orderbook(
        stock_code="005930",
        bids=bids,
        asks=asks,
    )
    assert len(fake_redis.published) == 1
    channel, raw = fake_redis.published[0]
    assert channel == "tp:market.orderbook.005930"
    payload = orjson.loads(raw)
    assert payload["stock_code"] == "005930"
    assert payload["bids"] == [[50000.0, 100], [49950.0, 200], [49900.0, 300]]
    assert payload["asks"] == [[50050.0, 150], [50100.0, 250], [50150.0, 350]]
    # 합산 잔량 자동 계산
    assert payload["total_bid_qty"] == 600
    assert payload["total_ask_qty"] == 750
    assert payload["source"] == "creon"
    assert "ts" in payload


@pytest.mark.asyncio
async def test_publish_orderbook_accepts_list_of_lists(fake_redis):
    """tuple 대신 list로 와도 처리되어야 한다."""
    event_publisher._redis = fake_redis  # type: ignore[assignment]

    await event_publisher.publish_orderbook(
        stock_code="000660",
        bids=[[12000, 10], [11990, 20]],
        asks=[[12010, 5], [12020, 15]],
        total_bid_qty=30,
        total_ask_qty=20,
    )
    _channel, raw = fake_redis.published[-1]
    payload = orjson.loads(raw)
    assert payload["total_bid_qty"] == 30
    assert payload["total_ask_qty"] == 20


# ---------------------------------------------------------------------------
# 2. MockCreonAdapter.get_orderbook
# ---------------------------------------------------------------------------
def test_mock_get_orderbook_returns_10_levels():
    adapter = get_adapter()
    assert isinstance(adapter, MockCreonAdapter)
    snap = adapter.get_orderbook("005930")
    assert isinstance(snap, OrderbookSnapshot)
    assert snap.code == "005930"
    assert len(snap.bids) == 10
    assert len(snap.asks) == 10
    # 매수는 1단계가 가장 높고, 매도는 1단계가 가장 낮아야 함
    bid_prices = [p for p, _ in snap.bids]
    ask_prices = [p for p, _ in snap.asks]
    assert bid_prices == sorted(bid_prices, reverse=True)
    assert ask_prices == sorted(ask_prices)
    # 최우선 매수 < 최우선 매도 (호가창 정합성)
    assert bid_prices[0] < ask_prices[0]
    # 합산 잔량 일치
    assert snap.total_bid_qty == sum(q for _, q in snap.bids)
    assert snap.total_ask_qty == sum(q for _, q in snap.asks)


def test_mock_get_orderbook_deterministic_for_code():
    """같은 종목은 (잔량 시드 기반이라) 동일 결과."""
    adapter = get_adapter()
    s1 = adapter.get_orderbook("035420")
    s2 = adapter.get_orderbook("035420")
    # 가격은 random.randint 영향으로 다를 수 있지만 잔량 구조는 deterministic
    assert [q for _, q in s1.bids] == [q for _, q in s2.bids]
    assert [q for _, q in s1.asks] == [q for _, q in s2.asks]


def test_subscribe_unsubscribe_orderbook_tracks_callbacks():
    adapter = get_adapter()
    assert isinstance(adapter, MockCreonAdapter)
    cnt = adapter.subscribe_orderbook(["005930", "000660"], callback=lambda s: None)
    assert cnt == 2
    assert set(adapter._orderbook_callbacks.keys()) == {"005930", "000660"}
    removed = adapter.unsubscribe_orderbook(["005930"])
    assert removed == 1
    assert set(adapter._orderbook_callbacks.keys()) == {"000660"}


# ---------------------------------------------------------------------------
# 3. _calc_tick_size
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "price,expected",
    [
        (1500, 1.0),
        (3000, 5.0),
        (15000, 10.0),
        (35000, 50.0),
        (100000, 100.0),
        (300000, 500.0),
        (600000, 1000.0),
    ],
)
def test_tick_size_brackets(price, expected):
    assert _calc_tick_size(price) == expected


# ---------------------------------------------------------------------------
# 4. MockOrderbookWorker
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_mock_orderbook_worker_publishes(fake_redis):
    """worker emit 한 번이 Redis로 발행되어야 한다."""
    event_publisher._redis = fake_redis  # type: ignore[assignment]
    from creon_gateway.mock_orderbook_worker import (
        MockOrderbookWorker,
        reset_mock_orderbook_worker,
    )

    reset_mock_orderbook_worker()
    worker = MockOrderbookWorker(interval_sec=0.05, default_codes=["005930"])
    await worker._emit_one("005930")
    assert any(
        ch == "tp:market.orderbook.005930" for ch, _ in fake_redis.published
    )


@pytest.mark.asyncio
async def test_mock_orderbook_worker_start_stop(fake_redis):
    """start() → 짧게 대기 → stop() 흐름이 안전하게 종료된다."""
    event_publisher._redis = fake_redis  # type: ignore[assignment]
    from creon_gateway.mock_orderbook_worker import (
        MockOrderbookWorker,
        reset_mock_orderbook_worker,
    )

    reset_mock_orderbook_worker()
    worker = MockOrderbookWorker(interval_sec=0.05, default_codes=["005930"])
    await worker.start()
    await asyncio.sleep(0.12)
    await worker.stop()
    # 최소 1회 이상 발행되었는지
    assert any(
        ch.startswith("tp:market.orderbook.") for ch, _ in fake_redis.published
    )


# ---------------------------------------------------------------------------
# 5. REST 엔드포인트 통합
# ---------------------------------------------------------------------------
class TestOrderbookEndpoint:
    def test_market_orderbook_returns_10_levels(self, app_client):
        r = app_client.get("/market/orderbook/005930")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        data = body["data"]
        assert data["code"] == "005930"
        assert len(data["bids"]) == 10
        assert len(data["asks"]) == 10
        # 페이로드 구조: [[price, qty], ...]
        for level in data["bids"] + data["asks"]:
            assert len(level) == 2
        assert data["total_bid_qty"] > 0
        assert data["total_ask_qty"] > 0

    def test_market_orderbook_requires_api_key(self, app_client):
        r = app_client.get(
            "/market/orderbook/005930", headers={"X-Gateway-Api-Key": ""}
        )
        assert r.status_code == 401
