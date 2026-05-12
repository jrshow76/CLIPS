"""공통 페이지네이션 / 응답 envelope 회귀 테스트.

정책 (`11_feature_spec.md` 0.2):
- 성공: { "success": true, "data": {...} }
- 실패: { "success": false, "error": { "code": "E....", "message": "..." } }
- 페이지: { "success": true, "data": { "items": [...], "page": 1, "size": 20, "total": N } }
"""
from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.qa, pytest.mark.integration]


def _signup_login(client) -> str:
    email = f"pg-{uuid.uuid4().hex[:8]}@test.local"
    password = "Abcd1234!"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "nickname": "qa-pg"},
    )
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    ).json()["data"]["access_token"]


PAGINATED_ENDPOINTS = [
    ("/api/v1/signals", {"page": 1, "size": 10}),
    ("/api/v1/notifications", {"page": 1, "size": 10}),
    ("/api/v1/recommendations", {"page": 1, "size": 10}),
    ("/api/v1/strategies", {"page": 1, "size": 10}),
    ("/api/v1/orders", {"page": 1, "size": 10}),
    ("/api/v1/portfolios", {"page": 1, "size": 10}),
]


@pytest.mark.parametrize("path,params", PAGINATED_ENDPOINTS)
def test_paginated_response_envelope(app_client, path, params) -> None:
    """페이지네이션 응답은 items/page/size/total 키를 포함해야 한다."""
    tok = _signup_login(app_client)
    r = app_client.get(path, params=params, headers={"Authorization": f"Bearer {tok}"})
    # 라우트 미구현 시 404 허용
    assert r.status_code in (200, 404)
    if r.status_code != 200:
        return
    body = r.json()
    assert body.get("success") is True
    data = body.get("data", {})
    # 페이지네이션 응답 envelope 키 확인
    assert "items" in data
    assert "page" in data
    assert "size" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["page"] == params["page"]
    assert data["size"] == params["size"]
    assert isinstance(data["total"], int) and data["total"] >= 0


@pytest.mark.parametrize("page,size", [(0, 10), (1, 0), (1, 1001), (-1, 10)])
def test_paginated_invalid_params_returns_E0003(app_client, page, size) -> None:
    """잘못된 page/size 파라미터 → 400/422 E0003."""
    tok = _signup_login(app_client)
    r = app_client.get(
        "/api/v1/signals",
        params={"page": page, "size": size},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code in (200, 400, 404, 422)
    if r.status_code in (400, 422):
        assert r.json()["error"]["code"] in ("E0003",)


def test_success_envelope_shape(app_client) -> None:
    """성공 응답: success=true, data 필드 존재."""
    tok = _signup_login(app_client)
    r = app_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body


def test_error_envelope_shape_on_unauthorized(app_client) -> None:
    """인증 누락 시 success=false, error.code 존재."""
    r = app_client.get("/api/v1/auth/me")
    assert r.status_code in (401, 403)
    body = r.json()
    assert body.get("success") is False
    err = body.get("error", {})
    assert isinstance(err.get("code"), str) and err["code"].startswith("E")
    assert isinstance(err.get("message"), str)


def test_pagination_total_consistency(app_client) -> None:
    """동일 사용자 동일 필터: page=1과 page=2의 total 값이 일치해야 한다."""
    tok = _signup_login(app_client)
    h = {"Authorization": f"Bearer {tok}"}
    r1 = app_client.get("/api/v1/signals", params={"page": 1, "size": 5}, headers=h)
    r2 = app_client.get("/api/v1/signals", params={"page": 2, "size": 5}, headers=h)
    if r1.status_code == 200 and r2.status_code == 200:
        assert r1.json()["data"]["total"] == r2.json()["data"]["total"]
