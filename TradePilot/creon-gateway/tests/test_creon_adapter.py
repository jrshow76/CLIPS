"""CreonAdapter 단위 테스트.

검증 대상:
- RateLimiter 슬라이딩 윈도우 (1초 / 4초)
- MockCreonAdapter 주문 흐름 (BUY, SELL, 잔고부족, 매도수량부족)
- 멱등성 키 매핑은 main에서 검증
- 에러 코드 매핑 (CREON → G0xxx)
- SIM / REAL 모드 계좌 접두사 필터링
- RealCreonAdapter (mock COM 객체로 시뮬레이션)
"""
from __future__ import annotations

import time

import pytest

from creon_gateway.config import settings
from creon_gateway.creon_adapter import (
    MockCreonAdapter,
    OrderSubmitRequest,
    CancelRequest,
    RateLimiter,
    RealCreonAdapter,
    map_creon_code,
    get_adapter,
)


# ---------------------------------------------------------------------------
# 1. 에러 코드 매핑 (TC-INT-025, 026, 034, 035 의존)
# ---------------------------------------------------------------------------
class TestErrorCodeMapping:
    def test_known_codes(self):
        assert map_creon_code(0) == "OK"
        assert map_creon_code(-100) == "G0001"
        assert map_creon_code(-101) == "G0002"
        assert map_creon_code(-307) == "G0011"
        assert map_creon_code(-308) == "G0011"
        assert map_creon_code(-310) == "G0012"
        assert map_creon_code(-311) == "G0013"
        assert map_creon_code(-312) == "G0014"
        assert map_creon_code(-901) == "G0020"
        assert map_creon_code(-902) == "G0030"

    def test_unknown_code_defaults_to_g0010(self):
        assert map_creon_code(-9999) == "G0010"


# ---------------------------------------------------------------------------
# 2. RateLimiter (TC-INT-050, 051, 053 의존)
# ---------------------------------------------------------------------------
class TestRateLimiter:
    def test_under_limit_no_wait(self):
        rl = RateLimiter(per_sec=5, per_4sec=20)
        # 5건 빠르게 호출
        for _ in range(5):
            waited = rl.acquire()
            assert waited == 0

    def test_per_sec_limit_blocks(self):
        rl = RateLimiter(per_sec=3, per_4sec=20)
        start = time.monotonic()
        for _ in range(5):
            rl.acquire()
        elapsed = time.monotonic() - start
        # 5건이 3/sec 제한이면 적어도 ~1초 대기
        assert elapsed >= 0.9

    def test_per_4sec_limit_blocks(self):
        rl = RateLimiter(per_sec=100, per_4sec=5)
        start = time.monotonic()
        for _ in range(7):
            rl.acquire()
        elapsed = time.monotonic() - start
        # 7건 / 4초 5건 제한 → 적어도 일부 대기 발생
        assert elapsed >= 0.5

    def test_snapshot(self):
        rl = RateLimiter(per_sec=10, per_4sec=40)
        for _ in range(3):
            rl.acquire()
        snap = rl.snapshot()
        assert snap["per_sec"] == 3
        assert snap["per_4sec"] == 3


# ---------------------------------------------------------------------------
# 3. MockCreonAdapter 주문 흐름 (TC-INT-020, 022, 025, 026)
# ---------------------------------------------------------------------------
class TestMockAdapterOrders:
    def test_buy_limit_success(self):
        a = MockCreonAdapter()
        req = OrderSubmitRequest(
            code="005930", side="BUY", qty=10, order_type="LIMIT", price=70000
        )
        resp = a.submit_order(req)
        assert resp.accepted is True
        assert resp.broker_order_no
        assert resp.raw_code == 0

        # 보유 확인
        positions = a.get_positions()
        assert any(p.code == "005930" and p.qty == 10 for p in positions)

    def test_buy_insufficient_cash(self):
        a = MockCreonAdapter()
        # 천문학적 비용 → 잔고 부족
        req = OrderSubmitRequest(
            code="005930",
            side="BUY",
            qty=999_999_999,
            order_type="LIMIT",
            price=70000,
        )
        resp = a.submit_order(req)
        assert resp.accepted is False
        assert resp.raw_code == -307
        assert "잔고" in resp.raw_msg

    def test_sell_without_position(self):
        a = MockCreonAdapter()
        req = OrderSubmitRequest(
            code="005930", side="SELL", qty=1, order_type="LIMIT", price=70000
        )
        resp = a.submit_order(req)
        assert resp.accepted is False
        assert resp.raw_code == -308

    def test_sell_after_buy(self):
        a = MockCreonAdapter()
        a.submit_order(
            OrderSubmitRequest(
                code="005930",
                side="BUY",
                qty=5,
                order_type="LIMIT",
                price=70000,
            )
        )
        resp = a.submit_order(
            OrderSubmitRequest(
                code="005930",
                side="SELL",
                qty=3,
                order_type="LIMIT",
                price=71000,
            )
        )
        assert resp.accepted is True
        positions = a.get_positions()
        # 잔여 2주
        pos = next((p for p in positions if p.code == "005930"), None)
        assert pos is not None
        assert pos.qty == 2

    def test_cancel(self):
        a = MockCreonAdapter()
        resp = a.cancel_order(
            CancelRequest(broker_order_no="100001", code="005930", qty=1)
        )
        assert resp.accepted is True


# ---------------------------------------------------------------------------
# 4. SIM / REAL 모드 토글 (TC-INT-010, 011)
# ---------------------------------------------------------------------------
class TestTradeEnvMode:
    def test_sim_mode_accounts(self, monkeypatch):
        monkeypatch.setenv("CREON_TRADE_ENV", "SIM")
        monkeypatch.setenv("CREON_ACCOUNT_PREFIX_SIM", "55")
        from creon_gateway.config import reload_settings

        s = reload_settings()
        assert s.is_sim_mode()
        assert s.expected_account_prefix() == "55"

        a = MockCreonAdapter()
        accounts = a.get_accounts()
        assert all(acc["account_no"].startswith("55") for acc in accounts)
        assert all(acc["trade_env"] == "SIM" for acc in accounts)

    def test_real_mode_accounts(self, monkeypatch):
        monkeypatch.setenv("CREON_TRADE_ENV", "REAL")
        monkeypatch.setenv("CREON_ACCOUNT_PREFIX_REAL", "01")
        from creon_gateway.config import reload_settings

        s = reload_settings()
        assert s.is_real_mode()
        assert s.expected_account_prefix() == "01"

        a = MockCreonAdapter()
        accounts = a.get_accounts()
        assert all(acc["account_no"].startswith("01") for acc in accounts)


# ---------------------------------------------------------------------------
# 5. 시세 / 종목마스터 (TC-INT-040, 041)
# ---------------------------------------------------------------------------
class TestQuoteAndMaster:
    def test_quote_deterministic_per_code(self):
        a = MockCreonAdapter()
        q1 = a.get_quote("005930")
        q2 = a.get_quote("005930")
        # base는 hash 기반이므로 동일 종목은 베이스가 같음 (±200 변동)
        assert abs(q1.price - q2.price) <= 500

    def test_master_known_codes(self):
        a = MockCreonAdapter()
        m = a.get_stock_master("005930")
        assert m.name == "삼성전자"
        assert m.market == "KOSPI"

        m2 = a.get_stock_master("000660")
        assert m2.name == "SK하이닉스"


# ---------------------------------------------------------------------------
# 6. 실시간 구독 (TC-INT-043, 044, 045)
# ---------------------------------------------------------------------------
class TestRealtimeSubscribe:
    def test_subscribe_unsubscribe(self):
        a = MockCreonAdapter()
        cnt = a.subscribe_realtime(["005930", "000660"])
        assert cnt == 2
        cnt2 = a.unsubscribe_realtime(["005930"])
        assert cnt2 == 1


# ---------------------------------------------------------------------------
# 7. RealCreonAdapter (mock COM) — TC-INT-002, 020 의존
# ---------------------------------------------------------------------------
class TestRealAdapterWithMockCOM:
    def test_real_adapter_initialize_with_mock_com(self, monkeypatch, mock_com):
        """RealCreonAdapter 가 mock COM 객체로 초기화 + 주문 흐름."""
        # pythoncom / win32com 모듈 mock 주입
        import sys
        from unittest.mock import MagicMock

        pythoncom = MagicMock()
        pythoncom.CoInitialize = MagicMock(return_value=None)
        win32com = MagicMock()
        win32com.client = mock_com

        sys.modules["pythoncom"] = pythoncom
        sys.modules["win32com"] = win32com
        sys.modules["win32com.client"] = mock_com

        try:
            adapter = RealCreonAdapter()
            assert adapter.connected is True
            assert adapter.account_loaded is True

            # 계좌 조회 — 모의투자 접두사 55 가 매칭되어야 함
            monkeypatch.setenv("CREON_TRADE_ENV", "SIM")
            monkeypatch.setenv("CREON_ACCOUNT_PREFIX_SIM", "55")
            from creon_gateway.config import reload_settings
            reload_settings()
            accs = adapter.get_accounts()
            assert len(accs) == 1
            assert accs[0]["account_no"].startswith("55")

            # 주문
            resp = adapter.submit_order(
                OrderSubmitRequest(
                    code="005930",
                    side="BUY",
                    qty=1,
                    order_type="LIMIT",
                    price=71000,
                )
            )
            assert resp.accepted is True
            assert resp.broker_order_no == "99999999"

            # 취소
            cancel_resp = adapter.cancel_order(
                CancelRequest(
                    broker_order_no="99999999", code="005930", qty=1
                )
            )
            assert cancel_resp.accepted is True

            # 시세
            quote = adapter.get_quote("005930")
            assert quote.price == 71200.0

            # 마스터
            m = adapter.get_stock_master("005930")
            assert m.name == "삼성전자"
            assert m.market == "KOSPI"
        finally:
            sys.modules.pop("pythoncom", None)
            sys.modules.pop("win32com", None)
            sys.modules.pop("win32com.client", None)


# ---------------------------------------------------------------------------
# 8. 시스템 상태 / 헬스
# ---------------------------------------------------------------------------
class TestSystemStatus:
    def test_status_includes_trade_env_and_counters(self):
        a = MockCreonAdapter()
        a.submit_order(
            OrderSubmitRequest(
                code="005930",
                side="BUY",
                qty=1,
                order_type="LIMIT",
                price=70000,
            )
        )
        s = a.system_status()
        assert s["trade_env"] == "SIM"
        assert s["mode"] == "mock"
        assert s["connected"] is True
        assert s["account_loaded"] is True
        assert s["request_count_1s"] >= 1
        assert s["rate_limit_per_sec"] >= 1


# ---------------------------------------------------------------------------
# 9. 팩토리 fallback
# ---------------------------------------------------------------------------
class TestAdapterFactory:
    def test_factory_returns_mock_when_force(self, monkeypatch):
        monkeypatch.setenv("CREON_FORCE_MOCK", "true")
        from creon_gateway.config import reload_settings
        reload_settings()
        adapter = get_adapter()
        assert isinstance(adapter, MockCreonAdapter)
