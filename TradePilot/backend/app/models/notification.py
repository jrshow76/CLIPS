"""알림 도메인 ORM (tp_notify 스키마).

DDL: `database/init/15_notification_domain.sql`
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notification(Base):
    """알림 큐 (월별 파티셔닝). PK=(id, created_at)."""

    __tablename__ = "notifications"
    __table_args__ = {"schema": "tp_notify"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="NORMAL")
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )


class NotificationChannel(Base):
    """사용자별 알림 채널 설정 (1:1)."""

    __tablename__ = "notification_channels"
    __table_args__ = {"schema": "tp_notify"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), primary_key=True
    )
    inapp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AlertRule(Base):
    """사용자 알림 룰."""

    __tablename__ = "alert_rules"
    __table_args__ = {"schema": "tp_notify"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="NORMAL")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
