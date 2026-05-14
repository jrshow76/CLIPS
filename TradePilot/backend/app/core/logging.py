"""구조화 로깅 설정.

structlog 기반으로 JSON 로그를 출력하고, trace_id 컨텍스트를 자동으로 포함한다.

본 모듈은 추가로 로그 페이로드의 민감 정보를 **자동 마스킹** 한다(SEC-009-FOLLOWUP).
- 마스킹 대상 키: password, token, otp, api_key, authorization, gpg, aes_key 등
- URL 쿼리 문자열의 token=...,api_key=... 도 함께 마스킹
- dict / list / tuple 재귀 순회 (깊이 5 제한, 성능 영향 < 5% 목표)
- **순수 함수**: 입력을 mutate 하지 않고 새 dict 를 반환
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config import settings


# =============================================================================
# 자동 마스킹 (SEC-009-FOLLOWUP)
# =============================================================================

# 마스킹 대치 문자열
_MASK_VALUE = "***MASKED***"

# 재귀 순회 최대 깊이 (성능 보호)
_MAX_RECURSION_DEPTH = 5

# 마스킹 대상 키 (소문자, 부분 매칭으로 사용 — case-insensitive)
# 키 이름에 아래 토큰이 하나라도 포함되면 값 전체를 마스킹한다.
# 주의: 너무 일반적인 단어(`key` 등 단독)는 피한다(예: `stock_key`, `order_key` 오탐).
_SENSITIVE_KEY_PATTERNS: tuple[str, ...] = (
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",          # access_token, refresh_token, reset_token 등 모두 매칭
    "otp",            # otp_code, otp_secret 도 포함
    "api_key",
    "apikey",
    "authorization",
    "private_key",
    "gpg",
    "aes_key",
    "aes",
    "creon_password",
    "cert_pw",
    "bank_account",
    "ssn",            # 주민등록번호 등 PII
    "credit_card",
)

# 마스킹 제외 키 (위 패턴에 매칭되더라도 평문 보존)
# 예: `csrf_token` 은 보안 토큰이지만 디버깅 가시성 우선
_MASK_EXCLUSION_KEYS: frozenset[str] = frozenset(
    {
        "csrf_token",
        "trace_id",       # trace_id 가 "...token..." 단어를 포함할 일은 없으나 명시
        "request_id",
    }
)

# URL 쿼리 마스킹: token=...&api_key=... 형태를 *** 로 대체
# 그룹 1: 키, 그룹 2: '=' 와 값
_URL_QUERY_MASK_RE = re.compile(
    r"(?i)\b(token|api_key|apikey|password|access_token|refresh_token|otp|secret)=([^&\s\"']+)"
)


def _is_sensitive_key(key: str) -> bool:
    """주어진 키 이름이 민감 키인지 판정.

    하이픈(`-`)/대소문자 변형을 흡수하기 위해 키를 정규화한 뒤 비교한다.
      예) `X-API-KEY` -> `x_api_key` -> `api_key` 패턴 매칭 성공
    """
    if not isinstance(key, str):
        return False
    key_lower = key.lower()
    # 하이픈을 언더스코어로 정규화(HTTP 헤더 호환)
    key_normalized = key_lower.replace("-", "_")
    if key_lower in _MASK_EXCLUSION_KEYS or key_normalized in _MASK_EXCLUSION_KEYS:
        return False
    for pattern in _SENSITIVE_KEY_PATTERNS:
        if pattern in key_normalized:
            return True
    return False


def _mask_url_query(value: str) -> str:
    """URL/쿼리 문자열 내 민감 파라미터 값을 마스킹."""
    if not isinstance(value, str) or "=" not in value:
        return value
    return _URL_QUERY_MASK_RE.sub(lambda m: f"{m.group(1)}={_MASK_VALUE}", value)


def _mask_value(value: Any, depth: int = 0) -> Any:
    """값을 재귀적으로 순회하며 민감 정보를 마스킹.

    Args:
        value: 마스킹 대상 값(dict/list/tuple/str/etc.)
        depth: 현재 재귀 깊이

    Returns:
        마스킹된 사본. 원본은 변경되지 않는다(순수 함수).
    """
    # 깊이 제한 — 그래프 형태의 입력에서 무한 재귀 방지
    if depth >= _MAX_RECURSION_DEPTH:
        return value

    if isinstance(value, dict):
        return {k: _mask_pair(k, v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_value(item, depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_value(item, depth + 1) for item in value)
    if isinstance(value, str):
        return _mask_url_query(value)
    return value


def _mask_pair(key: Any, value: Any, depth: int) -> Any:
    """(key, value) 쌍에 대해 키가 민감하면 값 전체 마스킹, 아니면 재귀 순회."""
    if isinstance(key, str) and _is_sensitive_key(key):
        # 값이 빈 문자열/None 이면 그대로 두어 로그 노이즈를 줄임
        if value in (None, ""):
            return value
        return _MASK_VALUE
    return _mask_value(value, depth)


def mask_sensitive_fields(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """structlog processor: event_dict 의 민감 정보를 자동 마스킹.

    structlog processor 시그니처: (logger, method_name, event_dict) -> event_dict

    - 입력 event_dict 를 mutate 하지 않고 새 dict 를 반환한다(순수 함수).
    - dict/list/tuple 을 최대 깊이 5 까지 재귀 순회한다.
    - 키 이름이 `_SENSITIVE_KEY_PATTERNS` 와 부분 매칭(case-insensitive) 되면 값을 `***MASKED***` 로 대치.
    - 문자열 값에 URL 쿼리(`token=...`, `api_key=...`) 가 포함되면 해당 부분만 마스킹.
    - 비즈니스 로직 영향 없음(로깅 시점에만 동작).
    """
    if not isinstance(event_dict, dict):
        return event_dict
    # 최상위 dict 도 동일 로직으로 처리
    return {k: _mask_pair(k, v, 1) for k, v in event_dict.items()}


# =============================================================================
# structlog / stdlib logging 설정
# =============================================================================


def configure_logging() -> None:
    """애플리케이션 시작 시 1회 호출하는 로깅 설정."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=False)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # 자동 마스킹: 렌더링 직전에 위치시켜 모든 가공된 필드를 커버
        mask_sensitive_fields,
    ]

    if settings.is_dev:
        # 개발 환경은 사람이 읽기 쉬운 컬러 출력
        renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # 운영 환경은 JSON
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # 표준 logging도 동일 수준으로 맞춤 (sqlalchemy/uvicorn 등)
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    # 시끄러운 라이브러리 톤다운
    for noisy in ("uvicorn.access", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    """모듈 단위 로거 헬퍼."""
    return structlog.get_logger(name) if name else structlog.get_logger()


def bind_trace(trace_id: str, **kwargs: Any) -> None:
    """현재 요청 컨텍스트에 trace_id 를 바인딩한다."""
    structlog.contextvars.bind_contextvars(trace_id=trace_id, **kwargs)


def clear_trace() -> None:
    """요청 종료 시 컨텍스트를 비운다."""
    structlog.contextvars.clear_contextvars()
