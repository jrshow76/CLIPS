"""사용자 도메인 Pydantic 스키마.

`docs/13_api_requirements.md` §2 명세 구현.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserMeOut(BaseModel):
    """GET /users/me 응답."""

    id: str  # public_id
    email: str
    nickname: str
    role: str
    trade_mode: Literal["SIM", "LIVE"]
    phone: str | None = None
    email_verified: bool
    phone_verified: bool
    created_at: str


class UserMeUpdateIn(BaseModel):
    """PATCH /users/me 요청 (부분 수정)."""

    model_config = ConfigDict(extra="forbid")

    nickname: str | None = Field(default=None, min_length=2, max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class UserSettingsOut(BaseModel):
    """사용자 설정 응답."""

    theme: Literal["light", "dark"] = "light"
    noti_inapp: bool = True
    noti_email: bool = True
    noti_telegram: bool = False
    noti_rules: dict[str, Any] = Field(default_factory=dict)
    schedule: dict[str, Any] = Field(default_factory=dict)


class UserSettingsUpdateIn(BaseModel):
    """사용자 설정 부분 수정."""

    model_config = ConfigDict(extra="forbid")

    theme: Literal["light", "dark"] | None = None
    noti_inapp: bool | None = None
    noti_email: bool | None = None
    noti_telegram: bool | None = None
    noti_rules: dict[str, Any] | None = None
    schedule: dict[str, Any] | None = None


class AdminUserItem(BaseModel):
    """관리자: 사용자 페이지 아이템."""

    id: str
    email: EmailStr
    nickname: str
    role: str
    trade_mode: str
    created_at: str
    last_login_at: str | None = None


class RoleUpdateIn(BaseModel):
    """PATCH /users/{id}/role 요청."""

    model_config = ConfigDict(extra="forbid")

    role: Literal[
        "ROLE_ADMIN", "ROLE_OPERATOR", "ROLE_TRADER_PRO", "ROLE_TRADER", "ROLE_GUEST"
    ]
