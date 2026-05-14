"""로그 자동 마스킹 단위 테스트 (SEC-009-FOLLOWUP).

대상: backend/app/core/logging.py 의 `mask_sensitive_fields` processor.

테스트 케이스:
1. 평면 dict — 민감 키 마스킹
2. 평면 dict — 비민감 키 유지
3. 중첩 dict 재귀 마스킹
4. 리스트/튜플 재귀 마스킹
5. URL 쿼리 마스킹
6. 마스킹 제외 키 (csrf_token, trace_id)
7. 빈 값(None/"") 은 마스킹하지 않음
8. 재귀 깊이 제한 (성능 보호)
9. 순수 함수 — 원본 mutate 하지 않음
10. processor 시그니처 호환성
"""
from __future__ import annotations

import pytest

from app.core.logging import (
    _MASK_VALUE,
    _is_sensitive_key,
    _mask_url_query,
    _mask_value,
    mask_sensitive_fields,
)


# =============================================================================
# 1. 평면 dict - 민감 키 마스킹
# =============================================================================


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "PASSWORD",         # case-insensitive
        "Password",
        "passwd",
        "user_password",    # 부분 매칭
        "secret",
        "access_token",
        "refresh_token",
        "reset_token",
        "otp",
        "otp_code",
        "api_key",
        "apikey",
        "X-API-KEY",        # 부분 매칭(소문자 포함)
        "authorization",
        "Authorization",
        "private_key",
        "gpg_key",
        "aes_key",
        "creon_password",
        "cert_pw",
        "bank_account",
        "ssn",
        "credit_card",
    ],
)
def test_민감_키는_마스킹된다(key: str) -> None:
    event = {key: "super-secret-value"}
    result = mask_sensitive_fields(None, "info", event)
    assert result[key] == _MASK_VALUE


# =============================================================================
# 2. 평면 dict - 비민감 키는 유지
# =============================================================================


@pytest.mark.parametrize(
    "key,value",
    [
        ("user_id", 123),
        ("email", "user@example.com"),
        ("order_id", "uuid-1234"),
        ("trace_id", "trace-abc"),
        ("status", "PENDING"),
        ("stock_code", "005930"),
        ("event", "order_created"),
        ("price", 70000),
    ],
)
def test_비민감_키는_평문_유지(key: str, value: object) -> None:
    event = {key: value}
    result = mask_sensitive_fields(None, "info", event)
    assert result[key] == value


# =============================================================================
# 3. 중첩 dict 재귀 마스킹
# =============================================================================


def test_중첩_dict_민감키_마스킹() -> None:
    event = {
        "event": "user_login",
        "request": {
            "email": "u@example.com",
            "password": "p@ssw0rd",
            "headers": {
                "authorization": "Bearer eyJxxx",
                "user-agent": "Mozilla",
            },
        },
    }
    result = mask_sensitive_fields(None, "info", event)
    assert result["request"]["password"] == _MASK_VALUE
    assert result["request"]["headers"]["authorization"] == _MASK_VALUE
    # 비민감 키 유지
    assert result["event"] == "user_login"
    assert result["request"]["email"] == "u@example.com"
    assert result["request"]["headers"]["user-agent"] == "Mozilla"


# =============================================================================
# 4. 리스트/튜플 재귀 마스킹
# =============================================================================


def test_list_내부_dict_마스킹() -> None:
    event = {
        "users": [
            {"email": "a@x.com", "password": "p1"},
            {"email": "b@x.com", "password": "p2"},
        ]
    }
    result = mask_sensitive_fields(None, "info", event)
    assert result["users"][0]["password"] == _MASK_VALUE
    assert result["users"][1]["password"] == _MASK_VALUE
    # 비민감 유지
    assert result["users"][0]["email"] == "a@x.com"


def test_tuple_내부_dict_마스킹() -> None:
    event = {
        "items": (
            {"name": "alice", "api_key": "ak-1"},
            {"name": "bob", "api_key": "ak-2"},
        )
    }
    result = mask_sensitive_fields(None, "info", event)
    assert isinstance(result["items"], tuple)
    assert result["items"][0]["api_key"] == _MASK_VALUE
    assert result["items"][1]["api_key"] == _MASK_VALUE


# =============================================================================
# 5. URL 쿼리 마스킹
# =============================================================================


@pytest.mark.parametrize(
    "url,expected_in",
    [
        (
            "https://api.example.com/ws?token=eyJabc.def.ghi",
            f"token={_MASK_VALUE}",
        ),
        (
            "https://api.example.com/foo?api_key=ak-12345",
            f"api_key={_MASK_VALUE}",
        ),
        (
            "https://api.example.com/x?password=hello&user=alice",
            f"password={_MASK_VALUE}",
        ),
        (
            "https://api.example.com/x?access_token=AAAA",
            f"access_token={_MASK_VALUE}",
        ),
        (
            "https://api.example.com/x?token=abc&api_key=def",
            # 두 개 모두 마스킹되어야 함
            "token=",
        ),
    ],
)
def test_URL_쿼리_민감_파라미터_마스킹(url: str, expected_in: str) -> None:
    masked = _mask_url_query(url)
    assert _MASK_VALUE in masked
    assert "eyJabc" not in masked
    assert "ak-12345" not in masked
    assert "hello" not in masked
    assert "AAAA" not in masked


def test_URL_쿼리_마스킹_event_dict_통합() -> None:
    event = {
        "event": "ws_connect",
        "url": "wss://api.example.com/ws/market?token=eyJabc.def.ghi",
        "method": "GET",
    }
    result = mask_sensitive_fields(None, "info", event)
    assert "eyJabc" not in result["url"]
    assert _MASK_VALUE in result["url"]
    # 비민감 필드 유지
    assert result["method"] == "GET"


def test_URL_쿼리에_민감_파라미터_없으면_변경_없음() -> None:
    url = "https://api.example.com/foo?bar=baz"
    assert _mask_url_query(url) == url


# =============================================================================
# 6. 마스킹 제외 키 (csrf_token, trace_id 등)
# =============================================================================


def test_csrf_token은_마스킹_제외() -> None:
    event = {"csrf_token": "csrf-abc-123"}
    result = mask_sensitive_fields(None, "info", event)
    assert result["csrf_token"] == "csrf-abc-123"


def test_trace_id_request_id는_마스킹_제외() -> None:
    event = {
        "trace_id": "trace-xyz",
        "request_id": "req-456",
    }
    result = mask_sensitive_fields(None, "info", event)
    assert result["trace_id"] == "trace-xyz"
    assert result["request_id"] == "req-456"


# =============================================================================
# 7. 빈 값(None/"") 은 마스킹하지 않음 (로그 노이즈 감소)
# =============================================================================


@pytest.mark.parametrize("empty_value", [None, ""])
def test_빈_값은_마스킹하지_않음(empty_value: object) -> None:
    event = {"password": empty_value}
    result = mask_sensitive_fields(None, "info", event)
    assert result["password"] == empty_value


# =============================================================================
# 8. 재귀 깊이 제한 (성능 보호)
# =============================================================================


def test_재귀_깊이_제한_무한루프_방어() -> None:
    """최대 깊이 5 를 초과하면 마스킹 중단(원본 유지) — 무한 재귀 방어."""
    # 깊이 7 의 중첩
    deep = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": {"l7": {"password": "p"}}}}}}}}
    # 예외 없이 처리되어야 함
    result = mask_sensitive_fields(None, "info", deep)
    assert isinstance(result, dict)
    # 깊이 5 이내는 마스킹되어야 함
    shallow = {"l1": {"l2": {"password": "p"}}}
    result2 = mask_sensitive_fields(None, "info", shallow)
    assert result2["l1"]["l2"]["password"] == _MASK_VALUE


# =============================================================================
# 9. 순수 함수 — 원본 mutate 하지 않음
# =============================================================================


def test_원본_dict는_변경되지_않음() -> None:
    original = {
        "password": "p@ssw0rd",
        "nested": {"api_key": "ak-1"},
        "list": [{"token": "t1"}],
    }
    import copy

    snapshot = copy.deepcopy(original)

    result = mask_sensitive_fields(None, "info", original)

    # 원본 그대로
    assert original == snapshot
    # 결과만 마스킹
    assert result["password"] == _MASK_VALUE
    assert result["nested"]["api_key"] == _MASK_VALUE
    assert result["list"][0]["token"] == _MASK_VALUE


# =============================================================================
# 10. processor 시그니처 호환성 (structlog 표준)
# =============================================================================


def test_processor_시그니처는_structlog_호환() -> None:
    """(_logger, _method_name, event_dict) -> event_dict 시그니처."""
    event = {"event": "test", "password": "x"}
    # structlog 가 호출하듯 positional 인자 3개로 호출
    result = mask_sensitive_fields(object(), "info", event)
    assert isinstance(result, dict)
    assert result["password"] == _MASK_VALUE


def test_event_dict가_dict가_아니면_그대로_반환() -> None:
    """비정상 입력 방어 — 예외를 발생시키지 않는다."""
    assert mask_sensitive_fields(None, "info", "not-a-dict") == "not-a-dict"  # type: ignore[arg-type]


# =============================================================================
# 11. 헬퍼 함수 단위 테스트
# =============================================================================


@pytest.mark.parametrize(
    "key,expected",
    [
        ("password", True),
        ("PASSWORD", True),
        ("user_password", True),
        ("access_token", True),
        ("csrf_token", False),  # 제외 키
        ("trace_id", False),
        ("request_id", False),
        ("user_id", False),
        ("email", False),
        ("stock_code", False),
        ("api_key", True),
        ("apikey", True),
        ("X-API-KEY", True),
        ("", False),
        (123, False),  # type: ignore[arg-type]
    ],
)
def test_is_sensitive_key(key: object, expected: bool) -> None:
    assert _is_sensitive_key(key) is expected  # type: ignore[arg-type]


def test_mask_value_원시_타입_불변() -> None:
    """str 외 원시 타입은 URL 쿼리 매칭이 없으면 그대로 반환."""
    assert _mask_value(42) == 42
    assert _mask_value(3.14) == 3.14
    assert _mask_value(True) is True
    assert _mask_value(None) is None


# =============================================================================
# 12. 실제 시나리오 — OTP / 비밀번호 재설정 토큰 회귀 방지
# =============================================================================


def test_OTP_시나리오_마스킹() -> None:
    """SEC-009 회귀 방지: OTP 코드 평문 로깅 시도해도 마스킹됨."""
    event = {
        "event": "otp_issued",
        "user_id": 42,
        "otp_code": "123456",  # 마스킹되어야 함
        "ttl_sec": 300,
    }
    result = mask_sensitive_fields(None, "info", event)
    assert result["otp_code"] == _MASK_VALUE
    assert result["user_id"] == 42
    assert result["ttl_sec"] == 300


def test_비밀번호_재설정_토큰_시나리오_마스킹() -> None:
    """SEC-009 회귀 방지: 비밀번호 재설정 토큰 평문 로깅 시도해도 마스킹됨."""
    event = {
        "event": "password_reset_requested",
        "email": "user@example.com",
        "reset_token": "abc.def.ghi.jkl",  # 마스킹되어야 함
    }
    result = mask_sensitive_fields(None, "info", event)
    assert result["reset_token"] == _MASK_VALUE
    assert result["email"] == "user@example.com"


def test_WebSocket_URL_토큰_마스킹_회귀방지() -> None:
    """SEC-007 회귀 방지: WebSocket URL 의 token 쿼리 마스킹."""
    event = {
        "event": "ws_connect",
        "url": "wss://api.tradepilot.com/ws/market?token=eyJ.actual.jwt",
        "client_ip": "1.2.3.4",
    }
    result = mask_sensitive_fields(None, "info", event)
    assert "eyJ.actual.jwt" not in result["url"]
    assert result["client_ip"] == "1.2.3.4"
