"""사용자 API 통합 테스트.

회원가입 → 로그인 → /users/me 조회/수정/설정 흐름.
DB와 Redis가 동작 중이어야 한다.
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@test.local"


def _signup_and_login(app_client) -> tuple[str, str]:
    """회원가입 + 로그인 헬퍼. (email, access_token) 반환."""
    email = _unique_email()
    pw = "Abcd1234!"
    r = app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "tester"},
    )
    assert r.status_code == 201
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200
    return email, r.json()["data"]["access_token"]


def test_get_me_returns_profile(app_client) -> None:
    email, token = _signup_and_login(app_client)
    r = app_client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["data"]["email"] == email
    assert body["data"]["trade_mode"] == "SIM"


def test_patch_me_updates_nickname(app_client) -> None:
    _, token = _signup_and_login(app_client)
    r = app_client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"nickname": "newnick"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["nickname"] == "newnick"


def test_settings_get_then_patch(app_client) -> None:
    _, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    # 조회
    r = app_client.get("/api/v1/users/me/settings", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["theme"] in ("light", "dark")
    # 수정
    r = app_client.patch(
        "/api/v1/users/me/settings",
        headers=headers,
        json={"theme": "dark", "noti_email": False},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["theme"] == "dark"
    assert data["noti_email"] is False


def test_unauthorized_returns_E0001(app_client) -> None:
    r = app_client.get("/api/v1/users/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "E0001"
