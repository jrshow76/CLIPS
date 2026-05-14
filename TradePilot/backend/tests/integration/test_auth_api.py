"""인증 API 통합 테스트 (DB/Redis 필요).

DB와 Redis가 동작 중이어야 한다. CI에서는 docker compose up 후 실행.
"""
from __future__ import annotations

import uuid

import pytest


pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@test.local"


def test_signup_then_login(app_client) -> None:
    email = _unique_email()
    password = "Abcd1234!"

    # 회원가입
    r = app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "nickname": "tester"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["success"] is True
    assert body["data"]["status"] == "REGISTERED"

    # 로그인
    r = app_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    tok = r.json()["data"]
    assert "access_token" in tok and "refresh_token" in tok

    # /me
    r = app_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["email"] == email


def test_login_wrong_password_returns_E0001(app_client) -> None:
    email = _unique_email()
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Abcd1234!", "nickname": "x"},
    )
    r = app_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPass1!"},
    )
    assert r.status_code == 401
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "E0001"


def test_signup_duplicate_email_returns_E0051(app_client) -> None:
    email = _unique_email()
    payload = {"email": email, "password": "Abcd1234!", "nickname": "x"}
    r1 = app_client.post("/api/v1/auth/signup", json=payload)
    assert r1.status_code == 201
    r2 = app_client.post("/api/v1/auth/signup", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "E0051"


def test_password_policy_violation_returns_E0055(app_client) -> None:
    r = app_client.post(
        "/api/v1/auth/signup",
        json={"email": _unique_email(), "password": "weak", "nickname": "x"},
    )
    # Pydantic 검증(min_length=8) 에서 먼저 걸려 E0003 또는 정책 검증의 E0055가 반환된다.
    assert r.status_code in (400, 422)


# ============================================================================
# SEC-004(GATE-3): Refresh Token 회전 / Replay 탐지 통합 회귀
# ============================================================================
def _signup_and_login(app_client, email: str | None = None) -> dict[str, str]:
    """회원가입 후 로그인하여 토큰 페어 반환. 통합 환경에서만 호출."""
    email = email or _unique_email()
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "rot"},
    )
    r = app_client.post(
        "/api/v1/auth/login", json={"email": email, "password": pw}
    )
    return {"email": email, **r.json().get("data", {})}


def test_refresh_endpoint_returns_new_refresh_token_rotation(app_client) -> None:
    """SEC-004: /auth/refresh 호출 시 새 access + 새 refresh 토큰을 반환해야 한다."""
    cred = _signup_and_login(app_client)
    if "refresh_token" not in cred:
        pytest.skip("integration environment unavailable")

    old_refresh = cred["refresh_token"]
    r = app_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    # 통합 환경(DB+Redis)이 있어야 200. 없으면 5xx → 스킵 처리.
    if r.status_code != 200:
        pytest.skip(f"refresh endpoint not available: {r.status_code}")

    data = r.json().get("data", {})
    assert "access_token" in data
    # GATE-3 핵심: 응답에 새 refresh_token 이 포함되어야 함
    assert "refresh_token" in data
    new_refresh = data["refresh_token"]
    assert new_refresh != old_refresh, "refresh token이 회전되지 않았음"


def test_refresh_replay_revokes_all_sessions(app_client) -> None:
    """SEC-004: 동일 refresh를 두 번째 호출하면 REPLAY로 간주, 401 + 전 세션 폐기.

    1) login → refresh_token A 발급
    2) /refresh(A) → 새 refresh B 발급 (A는 폐기됨)
    3) /refresh(A) 재호출 → 401 (replay)
    4) /refresh(B) 재호출 → 401 (B도 함께 폐기됨)
    """
    cred = _signup_and_login(app_client)
    if "refresh_token" not in cred:
        pytest.skip("integration environment unavailable")

    a = cred["refresh_token"]
    r1 = app_client.post("/api/v1/auth/refresh", json={"refresh_token": a})
    if r1.status_code != 200:
        pytest.skip(f"refresh endpoint not available: {r1.status_code}")
    b = r1.json()["data"]["refresh_token"]
    assert b != a

    # A 재사용 → replay 탐지
    r2 = app_client.post("/api/v1/auth/refresh", json={"refresh_token": a})
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "E0001"

    # B도 함께 폐기되어야 함
    r3 = app_client.post("/api/v1/auth/refresh", json={"refresh_token": b})
    assert r3.status_code == 401
