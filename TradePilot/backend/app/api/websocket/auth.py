"""WebSocket 인증 헬퍼.

WebSocket은 표준 HTTP Authorization 헤더 사용이 어려우므로 두 가지 방식을 지원한다.
1. **Query string 토큰**: ``?token=<jwt>`` (브라우저 친화)
2. **첫 메시지 인증**: ``{"type":"auth","token":"..."}`` (브라우저에서 토큰 노출 회피)

검증 실패 시 ``AuthFailure`` 예외 → 호출자가 close(1008)로 종료.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.security import decode_jwt_token


class AuthFailure(Exception):
    """WebSocket 인증 실패."""

    def __init__(self, message: str = "인증이 필요합니다.") -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class AuthenticatedClient:
    """인증된 WebSocket 클라이언트 컨텍스트.

    user_id는 access 토큰의 ``sub`` 클레임 (User.public_id) 값을 사용한다.
    """

    user_id: str
    role: str
    trade_mode: str
    raw_claims: dict[str, Any]


def authenticate_token(token: str) -> AuthenticatedClient:
    """JWT 문자열을 검증하고 ``AuthenticatedClient`` 반환.

    실패 시 :class:`AuthFailure` 발생.
    """
    if not token:
        raise AuthFailure("토큰이 비어있습니다.")
    try:
        payload = decode_jwt_token(token, expected_type="access")
    except Exception as e:  # AppException 포함
        raise AuthFailure(str(e)) from e

    sub = payload.get("sub")
    if not sub:
        raise AuthFailure("토큰에 sub 클레임이 없습니다.")
    return AuthenticatedClient(
        user_id=str(sub),
        role=str(payload.get("role", "ROLE_TRADER")),
        trade_mode=str(payload.get("trade_mode", "SIM")),
        raw_claims=payload,
    )
