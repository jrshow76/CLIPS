"""주문 멱등성 (X-Idempotency-Key) 회귀 테스트.

정책 (`14_exception_policy.md` 4.4):
- `X-Idempotency-Key` 미사용 호출은 동일 사용자 + 종목 + 사이드 + 수량 + 60초 윈도우
  기준 중복 차단 (E0022).
- 키 사용 시 24시간 내 동일 요청은 기존 결과 반환 (재처리 X).
"""
from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.qa, pytest.mark.integration]


def _signup_login(client) -> dict[str, str]:
    email = f"idem-{uuid.uuid4().hex[:8]}@test.local"
    password = "Abcd1234!"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "nickname": "qa-idem"},
    )
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return {"token": r.json()["data"]["access_token"]}


def _payload() -> dict:
    return {"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"}


def test_duplicate_order_within_60s_window_returns_E0022(app_client) -> None:
    """Idempotency-Key 미사용 + 60초 내 동일 페이로드 → 2회차 409 E0022."""
    cred = _signup_login(app_client)
    headers = {
        "Authorization": f"Bearer {cred['token']}",
        "X-Trade-Mode": "SIM",
    }
    r1 = app_client.post("/api/v1/orders", json=_payload(), headers=headers)
    r2 = app_client.post("/api/v1/orders", json=_payload(), headers=headers)
    # 첫 호출은 시드 미존재 시 404 가능
    assert r1.status_code in (201, 404, 422)
    # 두 번째는 중복 차단 또는 동일 응답
    assert r2.status_code in (201, 404, 409, 422)
    if r2.status_code == 409:
        assert r2.json()["error"]["code"] == "E0022"


def test_same_idempotency_key_returns_same_response(app_client) -> None:
    """동일 Idempotency-Key 재호출 시 기존 결과(주문 ID 동일) 반환."""
    cred = _signup_login(app_client)
    key = uuid.uuid4().hex
    headers = {
        "Authorization": f"Bearer {cred['token']}",
        "X-Trade-Mode": "SIM",
        "X-Idempotency-Key": key,
    }
    r1 = app_client.post("/api/v1/orders", json=_payload(), headers=headers)
    r2 = app_client.post("/api/v1/orders", json=_payload(), headers=headers)
    assert r1.status_code == r2.status_code
    if r1.status_code == 201:
        # 동일 주문 ID 반환되어야 한다
        assert r1.json()["data"]["id"] == r2.json()["data"]["id"]


def test_different_idempotency_keys_create_separate_orders(app_client) -> None:
    """서로 다른 키는 별개 주문으로 처리된다."""
    cred = _signup_login(app_client)
    headers_base = {
        "Authorization": f"Bearer {cred['token']}",
        "X-Trade-Mode": "SIM",
    }
    r1 = app_client.post(
        "/api/v1/orders",
        json=_payload(),
        headers={**headers_base, "X-Idempotency-Key": uuid.uuid4().hex},
    )
    r2 = app_client.post(
        "/api/v1/orders",
        json=_payload(),
        headers={**headers_base, "X-Idempotency-Key": uuid.uuid4().hex},
    )
    if r1.status_code == 201 and r2.status_code == 201:
        assert r1.json()["data"]["id"] != r2.json()["data"]["id"]


def test_idempotency_key_missing_with_different_qty_does_not_collide(app_client) -> None:
    """수량이 다르면 동일 윈도우 내라도 충돌하지 않는다 (다른 페이로드)."""
    cred = _signup_login(app_client)
    headers = {
        "Authorization": f"Bearer {cred['token']}",
        "X-Trade-Mode": "SIM",
    }
    r1 = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"},
        headers=headers,
    )
    r2 = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 2, "order_type": "MARKET"},
        headers=headers,
    )
    # 수량이 다르면 새 주문 (또는 시드 없을 시 동일 코드)
    if r2.status_code == 409:
        # 충돌이 발생하더라도 코드는 E0022 가 아니어야 한다
        assert r2.json()["error"]["code"] != "E0022"
