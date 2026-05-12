"""알림 API 통합 테스트.

채널 조회/수정, 알림 목록(빈 목록), 읽음 전체 처리.
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


def test_channels_default_then_update(app_client) -> None:
    token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}

    r = app_client.get("/api/v1/notifications/channels", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert "inapp_enabled" in data

    # telegram_chat_id 설정 + telegram 활성화
    r = app_client.patch(
        "/api/v1/notifications/channels",
        headers=headers,
        json={"telegram_enabled": True, "telegram_chat_id": "abc123"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["telegram_enabled"] is True
    assert data["telegram_chat_id"] == "abc123"


def test_list_notifications_empty(app_client) -> None:
    token = _signup_and_login(app_client)
    r = app_client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_read_all_returns_updated_count(app_client) -> None:
    token = _signup_and_login(app_client)
    r = app_client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["read"] is True
