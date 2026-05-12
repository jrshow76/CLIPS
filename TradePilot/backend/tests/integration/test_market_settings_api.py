"""시장/설정 API 통합 테스트.

장 운영상태 조회와 risk-limits 기본값 확인.
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def _signup_and_login(app_client) -> str:
    email = f"user-{uuid.uuid4().hex[:8]}@test.local"
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "t"},
    )
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    return r.json()["data"]["access_token"]


def test_market_status_returns_session(app_client) -> None:
    # 인증 불필요 (시장 상태)는 의도이지만 본 라우터는 인증 의존성 없이 동작
    r = app_client.get("/api/v1/market/status")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["session"] in ("PRE", "OPEN", "BREAK", "CLOSED")
    assert "holiday" in data


def test_calendar_for_2026(app_client) -> None:
    r = app_client.get("/api/v1/market/calendar?year=2026")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    # 2026년 신정 1월 1일 등 휴장 데이터가 포함되어야 함
    assert any(item["date"] == "2026-01-01" for item in body["data"])


def test_settings_risk_limits_default_then_update(app_client) -> None:
    token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}

    r = app_client.get("/api/v1/settings/risk-limits", headers=headers)
    assert r.status_code == 200, r.text
    default = r.json()["data"]
    assert "daily_buy_amount" in default

    # 수정
    r = app_client.put(
        "/api/v1/settings/risk-limits",
        headers=headers,
        json={"daily_buy_count": 30, "max_positions": 7},
    )
    assert r.status_code == 200, r.text
    updated = r.json()["data"]
    assert updated["daily_buy_count"] == 30
    assert updated["max_positions"] == 7


def test_trade_mode_default_is_sim(app_client) -> None:
    token = _signup_and_login(app_client)
    r = app_client.get(
        "/api/v1/settings/trade-mode",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["mode"] == "SIM"
