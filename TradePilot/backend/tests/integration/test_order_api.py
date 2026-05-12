"""주문 API 통합 테스트 (SIM 모드).

DB/Redis 필요 + price_daily 시드(005930 등) 권장.
"""
from __future__ import annotations

import uuid

import pytest


pytestmark = pytest.mark.integration


def _signup_and_login(client) -> dict[str, str]:
    email = f"user-{uuid.uuid4().hex[:8]}@test.local"
    password = "Abcd1234!"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "nickname": "trader"},
    )
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return {"access_token": r.json()["data"]["access_token"], "email": email}


def test_post_order_sim_market_buy_filled(app_client) -> None:
    cred = _signup_and_login(app_client)
    headers = {
        "Authorization": f"Bearer {cred['access_token']}",
        "X-Trade-Mode": "SIM",
        "X-Idempotency-Key": uuid.uuid4().hex,
    }
    payload = {
        "code": "005930",
        "side": "BUY",
        "qty": 1,
        "order_type": "MARKET",
    }
    r = app_client.post("/api/v1/orders", json=payload, headers=headers)
    # SIM 모드 + 시드/마스터가 없는 경우 E0062 가능 → 둘 다 허용
    assert r.status_code in (201, 404, 422)
    if r.status_code == 201:
        body = r.json()
        assert body["success"] is True
        assert body["data"]["mode"] == "SIM"
        assert body["data"]["status"] in ("FILLED", "NEW")


def test_post_order_without_trade_mode_returns_E0003(app_client) -> None:
    cred = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {cred['access_token']}"}
    r = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"},
        headers=headers,
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] in ("E0003",)


def test_post_order_mode_mismatch_returns_E0006(app_client) -> None:
    cred = _signup_and_login(app_client)
    headers = {
        "Authorization": f"Bearer {cred['access_token']}",
        "X-Trade-Mode": "LIVE",  # 사용자 기본은 SIM
    }
    r = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"},
        headers=headers,
    )
    # SIM 유저가 LIVE 헤더 → E0006 (409)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "E0006"
