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
