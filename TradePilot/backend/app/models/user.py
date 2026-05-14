"""사용자 도메인 ORM (tp_user 스키마).

DDL: `database/init/10_user_domain.sql`
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """사용자 마스터."""

    __tablename__ = "users"
    __table_args__ = {"schema": "tp_user"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, unique=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="ROLE_TRADER")
    trade_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="SIM")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disclaimer_agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    login_fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # D4 — 다증권사 어댑터: 사용자 선호 증권사 + 암호화된 자격증명 JSON.
    # 마이그레이션 ``2026_05_add_broker_settings.sql`` 적용 후 사용 가능.
    preferred_broker: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CREON"
    )
    broker_credentials: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role} mode={self.trade_mode}>"


class UserProfile(Base):
    """사용자 프로필 (1:1)."""

    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "tp_user"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), primary_key=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String)
    timezone: Mapped[str] = mapped_column(String(40), nullable=False, default="Asia/Seoul")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="ko-KR")
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserSettings(Base):
    """사용자 설정 (1:1)."""

    __tablename__ = "user_settings"
    __table_args__ = {"schema": "tp_user"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), primary_key=True
    )
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default="light")
    noti_inapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    noti_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    noti_telegram: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    noti_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    schedule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OtpCode(Base):
    """OTP 발급 이력 (단방향 해시 저장)."""

    __tablename__ = "otp_codes"
    __table_args__ = {"schema": "tp_user"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    otp_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, unique=True, server_default=func.gen_random_uuid()
    )
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Session(Base):
    """JWT Refresh Token 세션.

    SEC-004(GATE-3) 보강:
    - ``jti``: refresh 토큰의 고유 식별자. 매 회전마다 새 값.
    - ``replaced_by_jti``: 회전 체인 추적. 폐기된 세션이 어떤 jti로 대체되었는지 기록.
    - ``device_id``: 멀티 디바이스 환경에서 회전 체인 분리에 사용 (선택).
    - ``issued_at``: 토큰 최초 발급 시각.
    """

    __tablename__ = "sessions"
    __table_args__ = {"schema": "tp_user"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    # jti: 마이그레이션 적용 후에는 NOT NULL UNIQUE. 신규 발급은 항상 UUID 채움.
    jti: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, unique=True)
    device_id: Mapped[str | None] = mapped_column(String(64))
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(INET)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_jti: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserFavorite(Base):
    """사용자 즐겨찾기 종목 (user_id, stock_id PK)."""

    __tablename__ = "user_favorites"
    __table_args__ = {"schema": "tp_user"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), primary_key=True
    )
    stock_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditLogin(Base):
    """로그인 감사 로그."""

    __tablename__ = "audit_login"
    __table_args__ = {"schema": "tp_user"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="SET NULL")
    )
    event: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
