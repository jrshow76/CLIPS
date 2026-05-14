"""GATE-1~4 보안 수정 cross-cutting 회귀 보강 테스트 — GATE-5 (QA).

DB/Redis 없이 mock으로 동작하며, GATE-1(SEC-003) / GATE-2(SEC-001) /
GATE-3(SEC-004) / GATE-4(SEC-009)의 핵심 보장사항이 **다른 게이트의
수정으로 인해 손상되지 않았는지**를 단일 파일로 회귀 검증한다.

본 파일은 다음을 보장한다:

1. GATE-2 fail-fast: 운영 환경에서 약한 시크릿 감지 시 RuntimeError
2. GATE-2 정상 모드: 테스트 환경에서 정상 기동
3. GATE-4 마스킹 processor: GATE-3 refresh 토큰 payload도 자동 마스킹
4. GATE-4 마스킹 processor: GATE-1 cancel_order idempotency_key 헤더 마스킹
5. GATE-3 jti 발급: 동일 sub에 대해 매 호출 jti 가 unique
6. GATE-1 OrderRouterPort 시그니처: timeout_sec/idempotency_key 키워드 인자 수용
7. GATE-3 refresh 토큰의 jti 클레임이 GATE-4 로깅 마스킹과 충돌하지 않음
   (jti는 마스킹 대상이 아니어야 함 — trace 가능성 유지)
"""
from __future__ import annotations

import importlib
import inspect
import os
from uuid import uuid4

import pytest


pytestmark = [pytest.mark.qa, pytest.mark.unit]


# ---------------------------------------------------------------------------
# 1) GATE-2 fail-fast (SEC-001)
# ---------------------------------------------------------------------------
def test_gate2_production_weak_secret_fails_fast(monkeypatch):
    """GATE-2: 운영 환경에서 기본값/약한 시크릿 감지 시 RuntimeError 발생."""
    # `_validate_production_settings`를 직접 호출하기 위해 먼저 모듈을 import
    # (테스트 환경에서 안전하게 import 후 운영 모드 Settings 인스턴스 생성)
    from app.core.config import Settings, _validate_production_settings

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "change-this-in-production-please-32bytes-min")
    monkeypatch.setenv("AES_KEY", "base64-encoded-32byte-random-key")
    monkeypatch.setenv("CREON_GATEWAY_API_KEY", "replace-with-long-random-string")

    s = Settings()
    with pytest.raises(RuntimeError) as exc_info:
        _validate_production_settings(s)

    msg = str(exc_info.value)
    assert "SECURITY" in msg or "보안" in msg or "fail-fast" in msg
    assert "JWT_SECRET" in msg or "AES_KEY" in msg or "CREON" in msg


def test_gate2_test_env_normal_boot(monkeypatch):
    """GATE-2: 테스트 환경에서는 정상 기동(회귀 보호)."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-test")
    monkeypatch.setenv("AES_KEY", "test-aes-key-32-byte-test-key-12")

    import app.core.config as config_mod

    importlib.reload(config_mod)
    assert config_mod.settings.APP_ENV == "test"
    assert len(config_mod.settings.JWT_SECRET) >= 32

    # 정리 - 다른 테스트에 영향 없도록 기본값 복원
    monkeypatch.setenv("APP_ENV", "test")
    importlib.reload(config_mod)


# ---------------------------------------------------------------------------
# 2) GATE-4 마스킹 processor 회귀 (SEC-009)
# ---------------------------------------------------------------------------
def test_gate4_masks_refresh_token_payload_from_gate3():
    """GATE-4 마스킹이 GATE-3 refresh 응답 페이로드를 자동 마스킹한다."""
    from app.core.logging import mask_sensitive_fields

    event = {
        "event": "auth.refresh.rotated",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.rrr",
        "expires_in": 3600,
        "refresh_expires_in": 1209600,
        "user_id": 42,
    }
    masked = mask_sensitive_fields(None, "info", dict(event))

    assert masked["access_token"] == "***MASKED***"
    assert masked["refresh_token"] == "***MASKED***"
    # 비민감 필드는 보존
    assert masked["expires_in"] == 3600
    assert masked["refresh_expires_in"] == 1209600
    assert masked["user_id"] == 42


def test_gate4_masks_kill_switch_idempotency_header_from_gate1():
    """GATE-4 마스킹이 GATE-1 cancel_order 호출 시 헤더 컨텍스트를 보호한다."""
    from app.core.logging import mask_sensitive_fields

    event = {
        "event": "gateway.cancel_order",
        "url": "https://gw.tradepilot.local/orders/123/cancel?api_key=KEY123&trace=abc",
        "headers": {
            "Authorization": "Bearer eyJ-...",
            "X-Idempotency-Key": "killswitch:42:LIVE",
        },
        "order_id": 42,
        "duration_ms": 1234,
    }
    masked = mask_sensitive_fields(None, "info", dict(event))

    # URL 쿼리 api_key 마스킹
    assert "api_key=***" in masked["url"]
    # Authorization 헤더 마스킹
    assert masked["headers"]["Authorization"] == "***MASKED***"
    # idempotency key 자체는 비밀이 아니므로 그대로(추적용)
    assert masked["headers"]["X-Idempotency-Key"] == "killswitch:42:LIVE"
    # 비민감 필드 보존
    assert masked["order_id"] == 42
    assert masked["duration_ms"] == 1234


def test_gate4_does_not_mask_jti_or_trace_fields():
    """GATE-4 마스킹은 GATE-3 jti / GATE-1 trace_id 등 추적 식별자를 마스킹하지 않는다."""
    from app.core.logging import mask_sensitive_fields

    event = {
        "event": "auth.refresh.replay",
        "jti": "abc-def-1234",
        "trace_id": "uuid-trace",
        "request_id": "req-001",
        "user_id": 7,
        "password": "should-be-masked",
    }
    masked = mask_sensitive_fields(None, "warning", dict(event))

    assert masked["jti"] == "abc-def-1234"  # 마스킹 안 됨 (추적 식별자)
    assert masked["trace_id"] == "uuid-trace"
    assert masked["request_id"] == "req-001"
    assert masked["password"] == "***MASKED***"


# ---------------------------------------------------------------------------
# 3) GATE-3 jti 유일성 (SEC-004)
# ---------------------------------------------------------------------------
def test_gate3_jti_is_unique_per_issue():
    """GATE-3: 동일 sub로 매 호출마다 새 jti 발급."""
    from app.core.security import create_refresh_token_with_jti

    sub = str(uuid4())
    jtis = set()
    for _ in range(10):
        _, jti, _ = create_refresh_token_with_jti(subject=sub)
        jtis.add(jti)
    assert len(jtis) == 10, f"jti는 매 호출 unique 해야 하나, 중복 발생: {jtis}"


def test_gate3_refresh_token_carries_jti_claim():
    """GATE-3: 발급된 refresh 토큰 payload에 jti 클레임이 보존됨."""
    from app.core.security import create_refresh_token_with_jti, decode_jwt_token

    token, jti, ttl = create_refresh_token_with_jti(subject=str(uuid4()))
    payload = decode_jwt_token(token, expected_type="refresh")
    assert payload["jti"] == jti
    assert payload["type"] == "refresh"
    assert ttl > 0


# ---------------------------------------------------------------------------
# 4) GATE-1 OrderRouterPort 시그니처 (SEC-003)
# ---------------------------------------------------------------------------
def test_gate1_order_router_port_signature_accepts_timeout_and_idempotency():
    """GATE-1: OrderRouterPort.cancel_order 가 timeout_sec/idempotency_key 키워드를 수용."""
    from app.domains.ports.order_router_port import OrderRouterPort

    sig = inspect.signature(OrderRouterPort.cancel_order)
    params = sig.parameters
    assert "timeout_sec" in params, "GATE-1 회귀: timeout_sec 키워드 누락"
    assert "idempotency_key" in params, "GATE-1 회귀: idempotency_key 키워드 누락"


def test_gate1_live_router_signature_matches_port():
    """GATE-1: LIVE 라우터도 동일한 키워드 인자 시그니처를 준수."""
    from app.integrations.creon.live_order_router import LiveOrderRouter

    sig = inspect.signature(LiveOrderRouter.cancel_order)
    params = sig.parameters
    assert "timeout_sec" in params
    assert "idempotency_key" in params


def test_gate1_sim_router_signature_matches_port():
    """GATE-1: SIM 라우터도 (호환을 위해) 키워드를 받아야 한다."""
    from app.integrations.simulator.sim_order_router import SimOrderRouter

    sig = inspect.signature(SimOrderRouter.cancel_order)
    params = sig.parameters
    # SIM은 무시해도 무방하나 시그니처는 호환되어야 함
    assert "timeout_sec" in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    ), "GATE-1 회귀: SIM 라우터가 timeout_sec를 수용하지 않음"
    assert "idempotency_key" in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    ), "GATE-1 회귀: SIM 라우터가 idempotency_key를 수용하지 않음"


# ---------------------------------------------------------------------------
# 5) GATE-1 + GATE-4 통합: kill switch 로그 마스킹 시 SLA/카운트는 보존
# ---------------------------------------------------------------------------
def test_gate1_gate4_kill_switch_log_preserves_metrics():
    """Kill Switch 로그에서 metric 필드(duration_ms, canceled_count 등)는 보존되어야 한다."""
    from app.core.logging import mask_sensitive_fields

    event = {
        "event": "kill_switch.triggered",
        "user_id": 1,
        "trade_mode": "LIVE",
        "canceled_count": 5,
        "failed_count": 1,
        "duration_ms": 2480,
        "sla_violated": False,
        "trigger_source": "USER",
        "session_token": "eyJhbGc-...",  # 마스킹 대상
    }
    masked = mask_sensitive_fields(None, "info", dict(event))

    # 메트릭 보존
    assert masked["canceled_count"] == 5
    assert masked["failed_count"] == 1
    assert masked["duration_ms"] == 2480
    assert masked["sla_violated"] is False
    assert masked["trigger_source"] == "USER"
    # 토큰만 마스킹
    assert masked["session_token"] == "***MASKED***"
