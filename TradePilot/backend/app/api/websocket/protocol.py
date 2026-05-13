"""WebSocket 메시지 프로토콜.

클라이언트 ↔ 서버 메시지 스키마(Pydantic v2).
모든 메시지는 ``type`` 필드로 구분하며 JSON / snake_case / ISO8601 timestamp 규칙을 따른다.

서버→클라이언트:
- tick: 실시간 시세
- execution: 체결 이벤트
- notification: 시스템/매매 알림
- pong: heartbeat 응답
- error: 오류 (전송 후 close 가능)
- subscribed / unsubscribed: 구독 상태 변경 ack

클라이언트→서버:
- auth: 토큰 인증 (query string `?token=`로 미인증 연결 시 첫 메시지로 전송 가능)
- subscribe / unsubscribe: 종목 구독/해제
- ping: heartbeat
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# 종목 코드: 6자리 숫자 (KOSPI/KOSDAQ 공통 룰)
_STOCK_CODE_RE = re.compile(r"^\d{6}$")


def _now_iso() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 클라이언트 → 서버
# ---------------------------------------------------------------------------
class AuthRequest(BaseModel):
    """JWT 인증 요청 (첫 메시지)."""

    type: Literal["auth"] = "auth"
    token: str = Field(min_length=10, max_length=4096)


class SubscribeRequest(BaseModel):
    """종목 구독."""

    type: Literal["subscribe"] = "subscribe"
    stock_codes: list[str] = Field(min_length=1, max_length=50)

    @field_validator("stock_codes")
    @classmethod
    def _check_codes(cls, v: list[str]) -> list[str]:
        for code in v:
            if not _STOCK_CODE_RE.match(code):
                raise ValueError(f"잘못된 종목 코드: {code!r}")
        return list(dict.fromkeys(v))  # 중복 제거 (입력 순서 유지)


class UnsubscribeRequest(BaseModel):
    type: Literal["unsubscribe"] = "unsubscribe"
    stock_codes: list[str] = Field(min_length=1, max_length=50)

    @field_validator("stock_codes")
    @classmethod
    def _check_codes(cls, v: list[str]) -> list[str]:
        for code in v:
            if not _STOCK_CODE_RE.match(code):
                raise ValueError(f"잘못된 종목 코드: {code!r}")
        return list(dict.fromkeys(v))


class PingRequest(BaseModel):
    type: Literal["ping"] = "ping"
    ts: str | None = None


# ---------------------------------------------------------------------------
# 서버 → 클라이언트
# ---------------------------------------------------------------------------
class TickMessage(BaseModel):
    type: Literal["tick"] = "tick"
    stock_code: str
    price: float
    volume: int = 0
    change: float = 0.0
    change_pct: float = 0.0
    ts: str = Field(default_factory=_now_iso)
    event_id: str | None = None


class ExecutionMessage(BaseModel):
    type: Literal["execution"] = "execution"
    order_id: str | None = None
    broker_order_no: str | None = None
    stock_code: str
    side: Literal["BUY", "SELL"]
    qty: int
    price: float
    ts: str = Field(default_factory=_now_iso)
    event_id: str | None = None


class NotificationMessage(BaseModel):
    type: Literal["notification"] = "notification"
    notification_id: int | None = None
    title: str
    body: str | None = None
    severity: Literal["INFO", "WARN", "CRITICAL", "SUCCESS"] = "INFO"
    event_type: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=_now_iso)


class PongMessage(BaseModel):
    type: Literal["pong"] = "pong"
    ts: str = Field(default_factory=_now_iso)


class SubscribedAck(BaseModel):
    type: Literal["subscribed"] = "subscribed"
    stock_codes: list[str]
    total: int


class UnsubscribedAck(BaseModel):
    type: Literal["unsubscribed"] = "unsubscribed"
    stock_codes: list[str]
    total: int


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    details: dict[str, Any] | None = None


# 정책 위반 close code (RFC 6455)
WS_CLOSE_NORMAL = 1000
WS_CLOSE_POLICY_VIOLATION = 1008
WS_CLOSE_INTERNAL_ERROR = 1011
