"""알림 도메인 스키마."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationItem(BaseModel):
    id: int
    event_type: str
    priority: Literal["LOW", "NORMAL", "HIGH"] = "NORMAL"
    channel: str
    title: str
    body: str | None = None
    read: bool = False
    read_at: datetime | None = None
    created_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class ChannelOut(BaseModel):
    inapp_enabled: bool
    email_enabled: bool
    telegram_enabled: bool
    telegram_chat_id: str | None = None


class ChannelUpdateIn(BaseModel):
    """PATCH /notifications/channels."""

    model_config = ConfigDict(extra="forbid")

    inapp_enabled: bool | None = None
    email_enabled: bool | None = None
    telegram_enabled: bool | None = None
    telegram_chat_id: str | None = None


class TestSendIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["INAPP", "EMAIL", "TELEGRAM"]


# ----- Web Push (PWA) -----
class PushSubscribeIn(BaseModel):
    """POST /notifications/push/subscribe."""

    model_config = ConfigDict(extra="forbid")

    endpoint: str = Field(min_length=10, max_length=2048)
    p256dh_key: str = Field(min_length=10, max_length=512)
    auth_key: str = Field(min_length=10, max_length=128)
    user_agent: str | None = Field(default=None, max_length=512)
    expires_at: datetime | None = None


class PushUnsubscribeIn(BaseModel):
    """DELETE /notifications/push/unsubscribe (body)."""

    model_config = ConfigDict(extra="forbid")

    # 미지정 시 사용자의 모든 구독 해제
    endpoint: str | None = Field(default=None, min_length=10, max_length=2048)


class PushSubscriptionOut(BaseModel):
    id: int
    endpoint: str
    user_agent: str | None = None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime | None = None
    active: bool


class PushVapidKeyOut(BaseModel):
    public_key: str | None = None


class PushTestResult(BaseModel):
    sent: int
    failed: int
    expired: int = 0
    mock: bool = False
