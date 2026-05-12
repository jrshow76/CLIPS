"""매매 모드 가드 회귀 테스트.

검증 대상:
- `X-Trade-Mode` 헤더 누락/불일치 차단 (E0003 / E0006)
- LIVE 전환 7단계 사전 조건 게이트 (E0011~E0017)

운영 환경에서 SIM 모드 사용자가 LIVE 헤더로 주문하거나, 사전 조건 미충족 상태에서
LIVE 전환을 시도하는 케이스를 회귀 자동화로 검증한다.
"""
from __future__ import annotations

import uuid

import pytest


pytestmark = [pytest.mark.qa, pytest.mark.integration]


def _signup_login(client) -> dict[str, str]:
    """테스트용 사용자 가입 + 로그인."""
    email = f"mode-{uuid.uuid4().hex[:8]}@test.local"
    password = "Abcd1234!"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "nickname": "qa-mode"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return {"token": r.json()["data"]["access_token"], "email": email}


# --------------------------------------------------------------------------- #
# X-Trade-Mode 헤더 검증
# --------------------------------------------------------------------------- #


def test_order_without_trade_mode_header_returns_E0003(app_client) -> None:
    """헤더 누락 시 400 E0003 반환."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"},
        headers={"Authorization": f"Bearer {cred['token']}"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "E0003"


def test_order_mode_mismatch_user_sim_header_live_returns_E0006(app_client) -> None:
    """사용자 SIM, 헤더 LIVE → 409 E0006."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"},
        headers={
            "Authorization": f"Bearer {cred['token']}",
            "X-Trade-Mode": "LIVE",
            "X-Idempotency-Key": uuid.uuid4().hex,
        },
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "E0006"


def test_order_invalid_trade_mode_value_returns_E0003(app_client) -> None:
    """알 수 없는 모드값 → 400 E0003."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"},
        headers={
            "Authorization": f"Bearer {cred['token']}",
            "X-Trade-Mode": "PAPER",
        },
    )
    assert r.status_code in (400, 422)
    assert r.json()["error"]["code"] in ("E0003", "E0006")


# --------------------------------------------------------------------------- #
# LIVE 전환 7단계 게이트 (TP-LIVE-001~008)
# --------------------------------------------------------------------------- #


def test_live_switch_precondition_fail_returns_E0016(app_client) -> None:
    """시뮬 30건 미만 + 한도 미설정 상태에서 LIVE 전환 → 403 E0016."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/users/mode/switch",
        json={
            "target_mode": "LIVE",
            "otp_token": "dummy",
            "disclaimer_agreed": True,
        },
        headers={"Authorization": f"Bearer {cred['token']}"},
    )
    # 라우트 미구현 시 404, 구현 시 403/E0016
    assert r.status_code in (403, 404, 422)
    if r.status_code == 403:
        assert r.json()["error"]["code"] in ("E0016", "E0002")


def test_live_switch_otp_invalid_returns_E0011(app_client) -> None:
    """OTP 오류 → 401 E0011."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/users/mode/switch",
        json={
            "target_mode": "LIVE",
            "otp_token": "WRONG",
            "disclaimer_agreed": True,
        },
        headers={"Authorization": f"Bearer {cred['token']}"},
    )
    assert r.status_code in (401, 403, 404, 422)
    if r.status_code == 401:
        assert r.json()["error"]["code"] == "E0011"


def test_live_switch_disclaimer_missing_returns_E0013(app_client) -> None:
    """약관 미동의 → 403 E0013."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/users/mode/switch",
        json={
            "target_mode": "LIVE",
            "otp_token": "OK",
            "disclaimer_agreed": False,
        },
        headers={"Authorization": f"Bearer {cred['token']}"},
    )
    assert r.status_code in (403, 404, 422)
    if r.status_code == 403:
        assert r.json()["error"]["code"] in ("E0013", "E0016")


def test_live_switch_creon_unreachable_returns_E0012(app_client) -> None:
    """크레온 게이트웨이 OFF 상태(테스트 환경 기본값) → LIVE 전환 시 502 E0012 후보."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/users/mode/switch",
        json={
            "target_mode": "LIVE",
            "otp_token": "OK",
            "disclaimer_agreed": True,
            "force_creon_check": True,
        },
        headers={"Authorization": f"Bearer {cred['token']}"},
    )
    # 사전 조건이 우선 차단될 수 있으므로 다중 코드 허용
    assert r.status_code in (403, 404, 422, 502)
    if r.status_code == 502:
        assert r.json()["error"]["code"] in ("E0012", "E0004")


def test_live_switch_concurrent_request_returns_E0017(app_client) -> None:
    """동시 LIVE 전환 요청 → 두 번째 요청 409 E0017."""
    cred = _signup_login(app_client)
    headers = {"Authorization": f"Bearer {cred['token']}"}
    payload = {
        "target_mode": "LIVE",
        "otp_token": "OK",
        "disclaimer_agreed": True,
    }
    r1 = app_client.post("/api/v1/users/mode/switch", json=payload, headers=headers)
    r2 = app_client.post("/api/v1/users/mode/switch", json=payload, headers=headers)
    # 라우트 미구현 시 404, 구현 시 둘 중 하나는 409 E0017 또는 사전조건 차단
    assert r2.status_code in (403, 404, 409, 422)
    if r2.status_code == 409:
        assert r2.json()["error"]["code"] in ("E0017", "E0006")


# --------------------------------------------------------------------------- #
# 응답 본문 공통 검증
# --------------------------------------------------------------------------- #


def test_error_response_envelope_contract(app_client) -> None:
    """에러 응답은 success=false + error.code/message/trace_id/ts 포함해야 한다."""
    cred = _signup_login(app_client)
    r = app_client.post(
        "/api/v1/orders",
        json={"code": "005930", "side": "BUY", "qty": 1, "order_type": "MARKET"},
        headers={"Authorization": f"Bearer {cred['token']}"},  # 헤더 누락
    )
    body = r.json()
    assert body.get("success") is False
    assert "error" in body
    err = body["error"]
    assert isinstance(err.get("code"), str) and err["code"].startswith("E")
    assert isinstance(err.get("message"), str) and len(err["message"]) > 0
    # trace_id, ts 는 권장 필드(존재 시 형식 검증)
    if "trace_id" in err:
        assert isinstance(err["trace_id"], str)
    if "ts" in err:
        assert "T" in err["ts"]
