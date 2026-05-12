"""FastAPI 엔드포인트 통합 테스트.

TestClient + mock adapter 로 게이트웨이 HTTP API의 응답 envelope, 에러 매핑,
SIM/REAL 모드 분기, 멱등성 키 처리 등을 검증.
"""
from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# 1. 헬스 / 시스템
# ---------------------------------------------------------------------------
class TestSystemEndpoints:
    def test_healthz_includes_trade_env(self, app_client):
        r = app_client.get("/healthz")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["trade_env"] == "SIM"
        assert body["gateway_id"]

    def test_readyz_ok_in_mock_mode(self, app_client):
        r = app_client.get("/readyz")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["com_connected"] is True
        assert body["account_loaded"] is True
        assert body["trade_env"] == "SIM"

    def test_system_status_requires_api_key(self, app_client):
        # 키 제거
        r = app_client.get("/system/status", headers={"X-Gateway-Api-Key": ""})
        assert r.status_code == 401

    def test_system_status_with_valid_key(self, app_client):
        r = app_client.get("/system/status")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"]["trade_env"] == "SIM"

    def test_metrics_prometheus_format(self, app_client):
        r = app_client.get("/metrics")
        assert r.status_code == 200
        text = r.text
        assert "tradepilot_gateway_connected" in text
        assert "tradepilot_gateway_trade_env" in text
        assert "tradepilot_gateway_request_count_1s" in text

    def test_invalid_api_key_rejected(self, app_client):
        r = app_client.get(
            "/system/status",
            headers={"X-Gateway-Api-Key": "wrong-key"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 2. 계좌
# ---------------------------------------------------------------------------
class TestAccountEndpoints:
    def test_account_list_sim_mode(self, app_client):
        r = app_client.get("/account")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        data = body["data"]
        assert data["trade_env"] == "SIM"
        accounts = data["accounts"]
        assert len(accounts) >= 1
        # 모의투자 접두사 (테스트 환경 디폴트 "55")
        assert accounts[0]["account_no"].startswith(data["expected_prefix"])

    def test_balance(self, app_client):
        r = app_client.get("/account/balance")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "cash" in data
        assert "eval_amount" in data
        assert data["trade_env"] == "SIM"

    def test_positions_empty_initially(self, app_client):
        r = app_client.get("/account/positions")
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body["data"], list)


# ---------------------------------------------------------------------------
# 3. 주문
# ---------------------------------------------------------------------------
class TestOrderEndpoints:
    def test_submit_limit_buy_success(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "005930",
                "side": "BUY",
                "qty": 10,
                "order_type": "LIMIT",
                "price": 70000,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"]["accepted"] is True
        assert body["data"]["broker_order_no"]
        assert body["data"]["trade_env"] == "SIM"

    def test_submit_market_buy(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "005930",
                "side": "BUY",
                "qty": 1,
                "order_type": "MARKET",
            },
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_submit_limit_without_price_rejected(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "005930",
                "side": "BUY",
                "qty": 1,
                "order_type": "LIMIT",
            },
        )
        # pydantic 통과 후 G0012 반환 (price=None)
        body = r.json()
        assert body["success"] is False
        assert body["error"]["code"] == "G0012"

    def test_submit_invalid_code_length(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "12345",  # 5자리 (pydantic min=6)
                "side": "BUY",
                "qty": 1,
                "order_type": "LIMIT",
                "price": 1000,
            },
        )
        assert r.status_code == 422

    def test_submit_invalid_side(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "005930",
                "side": "INVALID",
                "qty": 1,
                "order_type": "LIMIT",
                "price": 1000,
            },
        )
        assert r.status_code == 422

    def test_submit_qty_zero_rejected(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "005930",
                "side": "BUY",
                "qty": 0,
                "order_type": "LIMIT",
                "price": 1000,
            },
        )
        assert r.status_code == 422

    def test_idempotency_returns_cached(self, app_client):
        """동일 idempotency_key 로 두 번 호출 → 동일 응답."""
        payload = {
            "code": "005930",
            "side": "BUY",
            "qty": 1,
            "order_type": "LIMIT",
            "price": 70000,
            "idempotency_key": "test-idem-001",
        }
        r1 = app_client.post("/orders", json=payload)
        r2 = app_client.post("/orders", json=payload)
        assert r1.json() == r2.json()
        # 동일 broker_order_no
        assert (
            r1.json()["data"]["broker_order_no"]
            == r2.json()["data"]["broker_order_no"]
        )

    def test_insufficient_cash_returns_g0011(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "005930",
                "side": "BUY",
                "qty": 999_999_999,
                "order_type": "LIMIT",
                "price": 70000,
            },
        )
        body = r.json()
        assert body["success"] is False
        assert body["error"]["code"] == "G0011"
        assert body["error"]["raw_code"] == -307

    def test_cancel_order(self, app_client):
        r = app_client.post(
            "/orders/100001/cancel",
            json={"broker_order_no": "100001", "code": "005930", "qty": 1},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"]["canceled"] is True


# ---------------------------------------------------------------------------
# 4. 시세
# ---------------------------------------------------------------------------
class TestMarketEndpoints:
    def test_quote(self, app_client):
        r = app_client.get("/market/quote/005930")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"]["code"] == "005930"
        assert body["data"]["price"] > 0

    def test_orderbook(self, app_client):
        r = app_client.get("/market/orderbook/005930")
        assert r.status_code == 200
        body = r.json()
        assert len(body["data"]["bids"]) == 10
        assert len(body["data"]["asks"]) == 10
        # 가격이 단조 증가/감소
        bids = body["data"]["bids"]
        asks = body["data"]["asks"]
        for i in range(len(bids) - 1):
            assert bids[i]["price"] > bids[i + 1]["price"]
        for i in range(len(asks) - 1):
            assert asks[i]["price"] < asks[i + 1]["price"]

    def test_stock_master(self, app_client):
        r = app_client.get("/stocks/master/005930")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["name"] == "삼성전자"
        assert data["market"] == "KOSPI"

    def test_subscribe_unsubscribe(self, app_client):
        r1 = app_client.post(
            "/subscribe/quote", json={"codes": ["005930", "000660"]}
        )
        assert r1.json()["data"]["subscribed"] == 2

        r2 = app_client.post(
            "/unsubscribe/quote", json={"codes": ["005930"]}
        )
        assert r2.json()["data"]["unsubscribed"] == 1


# ---------------------------------------------------------------------------
# 5. 응답 envelope 일관성
# ---------------------------------------------------------------------------
class TestResponseEnvelope:
    def test_success_envelope_shape(self, app_client):
        r = app_client.get("/system/status")
        body = r.json()
        assert "success" in body
        assert "data" in body
        assert body["success"] is True

    def test_error_envelope_shape(self, app_client):
        r = app_client.post(
            "/orders",
            json={
                "code": "005930",
                "side": "BUY",
                "qty": 999_999_999,
                "order_type": "LIMIT",
                "price": 70000,
            },
        )
        body = r.json()
        assert body["success"] is False
        assert "error" in body
        assert body["error"]["code"].startswith("G")
        assert "raw_code" in body["error"]
        assert "raw_msg" in body["error"]
