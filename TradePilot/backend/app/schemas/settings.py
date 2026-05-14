"""사용자 설정/한도/모드 전환 스키마."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TradeModeOut(BaseModel):
    mode: Literal["SIM", "LIVE"]
    switched_at: datetime | None = None


class TradeModeSwitchIn(BaseModel):
    """POST /settings/trade-mode/switch."""

    model_config = ConfigDict(extra="forbid")

    target: Literal["SIM", "LIVE"]
    otp_token: str | None = None
    terms_token: str | None = None


class RiskLimitOut(BaseModel):
    daily_buy_amount: Decimal
    daily_buy_count: int
    per_stock_amount: Decimal
    max_positions: int
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    daily_loss_limit_pct: Decimal
    single_order_max_qty: int


class RiskLimitUpdateIn(BaseModel):
    """PUT /settings/risk-limits."""

    model_config = ConfigDict(extra="forbid")

    daily_buy_amount: Decimal | None = None
    daily_buy_count: int | None = Field(default=None, ge=1, le=1000)
    per_stock_amount: Decimal | None = None
    max_positions: int | None = Field(default=None, ge=1, le=100)
    stop_loss_pct: Decimal | None = None
    take_profit_pct: Decimal | None = None
    daily_loss_limit_pct: Decimal | None = None
    single_order_max_qty: int | None = Field(default=None, ge=1, le=100000)


class KillSwitchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class CreonStatusOut(BaseModel):
    connected: bool
    account_masked: str | None = None
    last_check_at: datetime | None = None


class CreonTestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_token: str


class ScheduleOut(BaseModel):
    """사용자 스케줄 설정."""

    market_hours_only: bool = True
    pre_market_start: str = "08:30"
    post_market_end: str = "16:00"
    auto_kill_switch_loss_pct: Decimal | None = None


class ScheduleUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_hours_only: bool | None = None
    pre_market_start: str | None = None
    post_market_end: str | None = None
    auto_kill_switch_loss_pct: Decimal | None = None


# ---------------------------------------------------------------------------
# 알림 설정 (GET/PUT /settings/notifications)
# ---------------------------------------------------------------------------
class NotificationPrefOut(BaseModel):
    """알림 채널/룰 매핑 조회 응답."""

    inapp_enabled: bool
    email_enabled: bool
    kakao_enabled: bool  # 스키마 호환: 내부적으로 telegram_enabled 와 동일 컬럼
    sms_enabled: bool
    email: str | None = None
    phone: str | None = None
    quiet_hours_enabled: bool = False
    quiet_start: str = "22:00"
    quiet_end: str = "08:00"
    event_channel_map: dict[str, list[str]] = Field(default_factory=dict)


class NotificationPrefUpdateIn(BaseModel):
    """PUT /settings/notifications."""

    model_config = ConfigDict(extra="forbid")

    inapp_enabled: bool | None = None
    email_enabled: bool | None = None
    kakao_enabled: bool | None = None
    sms_enabled: bool | None = None
    quiet_hours_enabled: bool | None = None
    quiet_start: str | None = None
    quiet_end: str | None = None
    event_channel_map: dict[str, list[str]] | None = None


class NotificationTestIn(BaseModel):
    """POST /settings/notifications/test."""

    model_config = ConfigDict(extra="forbid")

    channel: Literal["INAPP", "EMAIL", "KAKAO", "SMS"]


class EmailVerifyRequestIn(BaseModel):
    """POST /settings/notifications/email/verify - 인증 코드 발송 요청."""

    model_config = ConfigDict(extra="forbid")

    email: str | None = None  # 미지정 시 사용자의 기본 이메일


class EmailVerifyConfirmIn(BaseModel):
    """POST /settings/notifications/email/verify (확인 단계)."""

    model_config = ConfigDict(extra="forbid")

    code: str
    otp_id: str


class KakaoOptInIn(BaseModel):
    """POST /settings/notifications/kakao/optin - 카카오 알림톡 수신 동의."""

    model_config = ConfigDict(extra="forbid")

    phone: str = Field(min_length=9, max_length=20)
    consent: bool = True
