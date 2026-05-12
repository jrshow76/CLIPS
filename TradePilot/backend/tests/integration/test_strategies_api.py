"""전략 API 통합 테스트.

POST → GET → PATCH → DELETE 라이프사이클.
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


def test_strategy_crud_flow(app_client) -> None:
    token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}

    # 생성
    payload = {
        "name": "RSI 과매도 매수",
        "description": "테스트 전략",
        "entry_rules": {"all": [{"indicator": "RSI", "op": "<", "value": 30}]},
        "exit_rules": {"all": [{"indicator": "RSI", "op": ">", "value": 70}]},
        "universe": ["005930"],
        "limits": {"max_positions": 5},
    }
    r = app_client.post("/api/v1/strategies", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    sid = r.json()["data"]["id"]

    # 조회
    r = app_client.get(f"/api/v1/strategies/{sid}", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["name"] == payload["name"]

    # 수정
    r = app_client.patch(
        f"/api/v1/strategies/{sid}",
        headers=headers,
        json={"name": "RSI 30 매수 (수정)"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "RSI 30 매수 (수정)"

    # 활성화 (SIM이라 OTP 불필요)
    r = app_client.patch(
        f"/api/v1/strategies/{sid}/activate",
        headers=headers,
        json={"active": True},
    )
    assert r.status_code == 200
    assert r.json()["data"]["active"] is True

    # 비활성화 후 삭제
    r = app_client.patch(
        f"/api/v1/strategies/{sid}/activate",
        headers=headers,
        json={"active": False},
    )
    assert r.status_code == 200
    r = app_client.delete(f"/api/v1/strategies/{sid}", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True


def test_strategy_invalid_rules_returns_E0003(app_client) -> None:
    token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    r = app_client.post(
        "/api/v1/strategies",
        headers=headers,
        json={
            "name": "잘못된 룰",
            "entry_rules": {"unknown": []},  # all/any/indicator 키 없음
            "exit_rules": {},
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "E0003"
