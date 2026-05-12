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
