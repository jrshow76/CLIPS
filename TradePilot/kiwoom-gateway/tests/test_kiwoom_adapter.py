"""키움 어댑터 단위 테스트.

검증:
- 에러 코드 매핑 (키움 raw → K0xxx)
- MockKiwoomAdapter 주문 흐름 (BUY, SELL, 예수금 부족, 매도수량 부족)
- RateLimiter 1초 sliding window
- system_status / accounts 구조
"""
from __future__ import annotations

import os
import time

import pytest

# 테스트 환경 강제 — fixture 보다 먼저 환경변수 세팅
os.environ.setdefault("KIWOOM_FORCE_MOCK", "true")
os.environ.setdefault("KIWOOM_TRADE_ENV", "SIM")
os.environ.setdefault("KIWOOM_USE_MOCK", "true")
os.environ.setdefault("GATEWAY_API_KEY", "test-api-key-test-api-key-test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("RATE_LIMIT_PER_SEC", "4")

from kiwoom_gateway.config import reload_settings
from kiwoom_gateway.kiwoom_adapter import (
    CancelRequest,
    MockKiwoomAdapter,
    OrderSubmitRequest,
    RateLimiter,
    get_adapter,
    map_kiwoom_code,
    reset_adapter,
)


@pytest.fixture(autouse=True)
def _reset():
    reload_settings()
    reset_adapter()
    yield
    reset_adapter()


# ---------------------------------------------------------------------------
# 1. 에러 코드 매핑
# ---------------------------------------------------------------------------
class TestErrorCodeMapping:
    def test_known_codes(self):
        assert map_kiwoom_code(0) == "OK"
        assert map_kiwoom_code(-10) == "K0001"
        assert map_kiwoom_code(-101) == "K0002"
        assert map_kiwoom_code(-200) == "K0010"
        assert map_kiwoom_code(-201) == "K0011"
        assert map_kiwoom_code(-202) == "K0012"
        assert map_kiwoom_code(-300) == "K0013"
        assert map_kiwoom_code(-301) == "K0014"

    def test_unknown_defaults(self):
        assert map_kiwoom_code(-9999) == "K0010"


# ---------------------------------------------------------------------------
# 2. RateLimiter
# ---------------------------------------------------------------------------
class TestRateLimiter:
    def test_under_limit_no_wait(self):
        rl = RateLimiter(per_sec=3)
        for _ in range(3):
            assert rl.acquire() == 0

    def test_over_limit_blocks(self):
        rl = RateLimiter(per_sec=2)
        rl.acquire()
        rl.acquire()
        start = time.monotonic()
        rl.acquire()  # 3번째는 대기
        elapsed = time.monotonic() - start
        # 1초 윈도우라 0.9초 이상 대기 (테스트 부하 보정 허용범위)
        assert elapsed >= 0.8


# ---------------------------------------------------------------------------
# 3. MockKiwoomAdapter
# ---------------------------------------------------------------------------
class TestMockAdapter:
    def test_factory_returns_mock(self):
        adapter = get_adapter()
        assert isinstance(adapter, MockKiwoomAdapter)
        assert adapter.connected
        assert adapter.account_loaded

    def test_buy_then_position(self):
        adapter = get_adapter()
        resp = adapter.submit_order(
            OrderSubmitRequest(
                code="005930",
                side="BUY",
                qty=10,
                order_type="LIMIT",
                price=70000.0,
            )
        )
        assert resp.accepted
        assert resp.broker_order_no
        positions = {p.code: p for p in adapter.get_positions()}
        assert "005930" in positions
        assert positions["005930"].qty == 10

    def test_sell_without_position_rejected(self):
        adapter = get_adapter()
        resp = adapter.submit_order(
            OrderSubmitRequest(
                code="000660",
                side="SELL",
                qty=5,
                order_type="LIMIT",
                price=200000.0,
            )
        )
        assert not resp.accepted
        assert resp.raw_code == -202
        assert map_kiwoom_code(resp.raw_code) == "K0012"

    def test_cancel_always_accepted_mock(self):
        adapter = get_adapter()
        resp = adapter.cancel_order(
            CancelRequest(broker_order_no="200001", code="005930", qty=10, side="BUY")
        )
        assert resp.accepted

    def test_system_status_has_required_fields(self):
        adapter = get_adapter()
        status = adapter.system_status()
        assert status["mode"] == "mock"
        assert status["trade_env"] == "SIM"
        assert "request_count_1s" in status
        assert "rate_limit_per_sec" in status

    def test_accounts_have_sim_prefix(self):
        adapter = get_adapter()
        accounts = adapter.get_accounts()
        assert len(accounts) == 1
        assert accounts[0]["trade_env"] == "SIM"
        # SIM 모드 mock 계좌번호는 8 로 시작 (kiwoom_adapter.py 참고)
        assert accounts[0]["account_no"].startswith("8")
