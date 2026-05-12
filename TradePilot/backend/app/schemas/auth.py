"""인증 도메인 Pydantic 스키마 (v2).

`docs/13_api_requirements.md` §1 명세를 따른다.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    """회원가입 요청."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=32)
    nickname: str = Field(min_length=2, max_length=50)


class SignupResponse(BaseModel):
    user_id: str
    status: str = "REGISTERED"


class LoginRequest(BaseModel):
    """로그인 요청."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str


class TokenPair(BaseModel):
    """access + refresh 토큰 쌍."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """현재 사용자 정보."""

    id: str  # public_id
    email: str
    nickname: str
    role: str
    trade_mode: Literal["SIM", "LIVE"]
    email_verified: bool
    phone_verified: bool
    created_at: str


class OtpSendRequest(BaseModel):
    """OTP 발급 요청."""

    model_config = ConfigDict(extra="forbid")

    phone: str | None = None  # SMS 채널 시 필수, EMAIL 시 None 허용
    purpose: Literal["LOGIN", "SIGNUP", "TRADE_MODE", "PASSWORD_RESET", "OTHER"] = "TRADE_MODE"
    channel: Literal["SMS", "EMAIL"] = "EMAIL"


class OtpSendResponse(BaseModel):
    otp_id: str
    expires_in: int


class OtpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    otp_id: str
    code: str = Field(min_length=4, max_length=8)


class OtpVerifyResponse(BaseModel):
    otp_token: str  # 단기 검증 토큰 (모드 전환 등에 사용)
    verified: bool = True


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str = Field(min_length=8, max_length=32)


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=32)


class LogoutResponse(BaseModel):
    logged_out: bool = True
