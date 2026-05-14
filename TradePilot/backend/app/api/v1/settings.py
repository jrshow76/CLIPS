"""설정 API 라우터.

`docs/13_api_requirements.md` §15 명세 구현.
모드 전환, 한도 조회/수정, Kill Switch, 크레온 상태, 스케줄.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, TradeModeDep
from app.core.response import success_response
from app.schemas.settings import (
    CreonStatusOut,
    CreonTestIn,
    EmailVerifyConfirmIn,
    EmailVerifyRequestIn,
    KakaoOptInIn,
    KillSwitchIn,
    NotificationPrefOut,
    NotificationPrefUpdateIn,
    NotificationTestIn,
    RiskLimitOut,
    RiskLimitUpdateIn,
    ScheduleOut,
    ScheduleUpdateIn,
    TradeModeOut,
    TradeModeSwitchIn,
)
from app.services.kill_switch_service import KillSwitchService
from app.services.notification_service import NotificationService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# 매매 모드
# ---------------------------------------------------------------------------
@router.get("/trade-mode", summary="현재 매매 모드")
async def get_trade_mode(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = SettingsService(db)
    data = await svc.get_trade_mode(user)
    return success_response(TradeModeOut(**data))


@router.post("/trade-mode/switch", summary="매매 모드 전환")
async def switch_trade_mode(
    payload: TradeModeSwitchIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SettingsService(db)
    data = await svc.switch_trade_mode(
        user=user,
        target=payload.target,
        otp_token=payload.otp_token,
        terms_token=payload.terms_token,
    )
    return success_response(TradeModeOut(**data))


# ---------------------------------------------------------------------------
# 한도
# ---------------------------------------------------------------------------
@router.get("/risk-limits", summary="매매 한도 조회")
async def get_limits(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = SettingsService(db)
    limits = await svc.get_limits(user.id)
    return success_response(
        RiskLimitOut(
            daily_buy_amount=limits.daily_buy_amount,
            daily_buy_count=limits.daily_buy_count,
            per_stock_amount=limits.per_stock_amount,
            max_positions=limits.max_positions,
            stop_loss_pct=limits.stop_loss_pct,
            take_profit_pct=limits.take_profit_pct,
            daily_loss_limit_pct=limits.daily_loss_limit_pct,
            single_order_max_qty=limits.single_order_max_qty,
        )
    )


@router.put("/risk-limits", summary="매매 한도 수정")
async def update_limits(
    payload: RiskLimitUpdateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SettingsService(db)
    patch = payload.model_dump(exclude_unset=True)
    limits = await svc.update_limits(user.id, **patch)
    return success_response(
        RiskLimitOut(
            daily_buy_amount=limits.daily_buy_amount,
            daily_buy_count=limits.daily_buy_count,
            per_stock_amount=limits.per_stock_amount,
            max_positions=limits.max_positions,
            stop_loss_pct=limits.stop_loss_pct,
            take_profit_pct=limits.take_profit_pct,
            daily_loss_limit_pct=limits.daily_loss_limit_pct,
            single_order_max_qty=limits.single_order_max_qty,
        )
    )


# ---------------------------------------------------------------------------
# Kill Switch (SEC-003 / GATE-1)
# ---------------------------------------------------------------------------
@router.post("/kill-switch", summary="비상정지")
async def kill_switch(
    payload: KillSwitchIn,
    user: CurrentUser,
    mode: TradeModeDep,
    db: AsyncSession = Depends(get_db),
):
    """비상정지 (Kill Switch).

    SEC-003(GATE-1):
    - 모드와 무관하게 라우터의 cancel_order를 호출하여 미체결을 정리한다.
    - SLA 5초 보장. 초과 시 부분결과 반환 + `tp:gateway.killswitch_partial` 이벤트.
    - 부분 실패 시 E0015 (502).
    """
    svc = KillSwitchService(db)
    result = await svc.trigger(
        user_id=user.id,
        trade_mode=mode,
        trigger_type="USER",
        trigger_source="USER",
        reason=payload.reason,
    )
    return success_response(
        {
            "canceled_orders": result["canceled_orders"],
            "failed": result["failed"],
            "mode_switched": result["mode_switched"],
            "duration_ms": result["duration_ms"],
            "sla_violated": result["sla_violated"],
        }
    )


# ---------------------------------------------------------------------------
# 스케줄
# ---------------------------------------------------------------------------
@router.get("/schedules", summary="스케줄 조회")
async def get_schedule(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = SettingsService(db)
    data = await svc.get_schedule(user.id)
    # ScheduleOut으로 모델링 (없는 키는 기본값)
    return success_response(
        ScheduleOut(
            market_hours_only=bool(data.get("market_hours_only", True)),
            pre_market_start=str(data.get("pre_market_start", "08:30")),
            post_market_end=str(data.get("post_market_end", "16:00")),
            auto_kill_switch_loss_pct=data.get("auto_kill_switch_loss_pct"),
        )
    )


@router.put("/schedules", summary="스케줄 수정")
async def update_schedule(
    payload: ScheduleUpdateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SettingsService(db)
    patch = payload.model_dump(exclude_unset=True)
    data = await svc.update_schedule(user.id, **patch)
    return success_response(
        ScheduleOut(
            market_hours_only=bool(data.get("market_hours_only", True)),
            pre_market_start=str(data.get("pre_market_start", "08:30")),
            post_market_end=str(data.get("post_market_end", "16:00")),
            auto_kill_switch_loss_pct=data.get("auto_kill_switch_loss_pct"),
        )
    )


# ---------------------------------------------------------------------------
# Creon 연결
# ---------------------------------------------------------------------------
@router.get("/creon", summary="크레온 연결 상태")
async def creon_status(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = SettingsService(db)
    data = await svc.get_creon_status(user.id)
    return success_response(CreonStatusOut(**data))


@router.post("/creon/test", summary="크레온 연결 테스트")
async def creon_test(
    payload: CreonTestIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SettingsService(db)
    data = await svc.test_creon(user.id, payload.password_token)
    return success_response(data)


# ---------------------------------------------------------------------------
# 알림 설정 (이메일/카카오 알림톡/SMS 통합)
# ---------------------------------------------------------------------------
@router.get("/notifications", summary="알림 설정 조회")
async def get_notification_settings(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """채널별 on/off, 등록된 이메일/전화번호, 이벤트→채널 매핑을 반환."""
    svc = NotificationService(db)
    ch = await svc.get_channels(user.id)
    return success_response(
        NotificationPrefOut(
            inapp_enabled=ch.inapp_enabled,
            email_enabled=ch.email_enabled,
            kakao_enabled=ch.telegram_enabled,  # 스키마 호환
            sms_enabled=ch.email_enabled or ch.telegram_enabled,
            email=user.email,
            phone=getattr(user, "phone", None),
            event_channel_map={
                "SIGNAL": ["INAPP", "EMAIL"],
                "ORDER_FILLED": ["INAPP", "EMAIL"],
                "KILL_SWITCH": ["INAPP", "EMAIL", "KAKAO", "SMS"],
                "SECURITY": ["INAPP", "EMAIL", "KAKAO"],
                "DAILY_REPORT": ["EMAIL", "KAKAO"],
            },
        )
    )


@router.put("/notifications", summary="알림 설정 수정")
async def update_notification_settings(
    payload: NotificationPrefUpdateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """채널별 on/off, 야간 조용 모드, 이벤트→채널 매핑 수정."""
    svc = NotificationService(db)
    # 카카오/SMS 토글은 telegram_enabled 컬럼을 공용으로 사용 (DDL 마이그레이션 전)
    kakao = payload.kakao_enabled if payload.kakao_enabled is not None else payload.sms_enabled
    ch = await svc.update_channels(
        user.id,
        inapp_enabled=payload.inapp_enabled,
        email_enabled=payload.email_enabled,
        telegram_enabled=kakao,
    )
    return success_response(
        NotificationPrefOut(
            inapp_enabled=ch.inapp_enabled,
            email_enabled=ch.email_enabled,
            kakao_enabled=ch.telegram_enabled,
            sms_enabled=ch.email_enabled or ch.telegram_enabled,
            email=user.email,
            phone=getattr(user, "phone", None),
            quiet_hours_enabled=bool(payload.quiet_hours_enabled),
            quiet_start=payload.quiet_start or "22:00",
            quiet_end=payload.quiet_end or "08:00",
            event_channel_map=payload.event_channel_map or {},
        )
    )


@router.post("/notifications/test", summary="알림 테스트 발송")
async def test_notification(
    payload: NotificationTestIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """선택한 채널로 테스트 알림을 즉시 발송."""
    svc = NotificationService(db)
    data = await svc.send_test(user.id, channel=payload.channel)
    return success_response(data)


@router.post("/notifications/email/verify", summary="이메일 인증 코드 발송/확인")
async def email_verify(
    payload: EmailVerifyRequestIn | EmailVerifyConfirmIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """이메일 인증 코드 발송(요청) 또는 확인.

    - 요청: ``EmailVerifyRequestIn`` (email 선택) → OTP 발급 + 이메일 발송
    - 확인: ``EmailVerifyConfirmIn`` (otp_id + code) → 검증 + 인증 플래그 처리
    """
    from app.services.auth_service import AuthService

    auth = AuthService(db)
    if isinstance(payload, EmailVerifyConfirmIn):
        token = await auth.verify_otp(payload.otp_id, payload.code)
        return success_response({"verified": True, "token": token})
    # 발송
    otp_id, ttl = await auth.send_otp(
        user_id=user.id,
        purpose="EMAIL_VERIFY",
        channel="EMAIL",
    )
    return success_response({"otp_id": otp_id, "ttl_sec": ttl})


# ---------------------------------------------------------------------------
# 다증권사 (Broker) — D4 다증권사 어댑터
# ---------------------------------------------------------------------------
@router.get("/brokers", summary="사용 가능한 증권사 목록")
async def list_brokers(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """사용 가능한 증권사 카탈로그 + 현재 사용자의 연결 상태.

    응답:
    - ``brokers``: ``[{name, broker, api_type, supports_markets, requires_windows, ...}]``
    - ``preferred``: 사용자 선호 broker
    - ``connected``: 자격증명 등록된 broker 목록
    """
    from app.domains.brokers import list_broker_infos

    creds: dict[str, Any] = getattr(user, "broker_credentials", {}) or {}
    items = []
    for info in list_broker_infos():
        items.append(
            {
                "broker": info.broker.value,
                "name": info.name,
                "api_type": info.api_type.value,
                "supports_markets": list(info.supports_markets),
                "requires_windows": info.requires_windows,
                "supports_sim": info.supports_sim,
                "supports_real": info.supports_real,
                "recommended": info.recommended,
                "notes": info.notes,
                "connected": info.broker.value in creds,
            }
        )
    return success_response(
        {
            "brokers": items,
            "preferred": getattr(user, "preferred_broker", "CREON"),
            "connected": sorted(creds.keys()),
        }
    )


@router.put("/brokers/preference", summary="선호 증권사 설정")
async def set_preferred_broker(
    payload: dict,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """사용자 선호 증권사 변경.

    Body: ``{"broker": "KIS" | "CREON" | "KIWOOM"}``
    """
    from sqlalchemy import update

    from app.core.exceptions import AppException
    from app.domains.brokers import Broker
    from app.models.user import User as UserModel

    raw = (payload or {}).get("broker")
    try:
        chosen = Broker(str(raw).upper()) if raw else None
    except ValueError:
        chosen = None
    if chosen is None:
        raise AppException("E0003", message="지원하지 않는 증권사입니다.")

    await db.execute(
        update(UserModel)
        .where(UserModel.id == user.id)
        .values(preferred_broker=chosen.value)
    )
    await db.commit()
    return success_response({"preferred": chosen.value})


@router.post("/brokers/{broker}/connect", summary="증권사 자격증명 등록")
async def connect_broker(
    broker: str,
    payload: dict,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """증권사 자격증명을 AES-256-GCM 암호화하여 ``broker_credentials`` JSON에 저장.

    KIS 예시:
    ```
    POST /settings/brokers/KIS/connect
    { "appkey": "...", "appsecret": "...", "account_no": "...", "account_prod_cd": "01" }
    ```

    키움 예시 (계좌번호만 — 게이트웨이가 로그인 처리):
    ```
    POST /settings/brokers/KIWOOM/connect
    { "account_no": "..." }
    ```
    """
    from datetime import datetime, timezone

    from sqlalchemy import update

    from app.core.exceptions import AppException
    from app.core.security import aes_encrypt
    from app.domains.brokers import Broker
    from app.models.user import User as UserModel

    try:
        chosen = Broker(broker.upper())
    except ValueError:
        raise AppException("E0003", message="지원하지 않는 증권사입니다.")

    body = payload or {}
    # 평문 비밀은 즉시 AES 암호화. JSON에는 ``_enc`` 접미사로만 저장.
    creds: dict[str, Any] = dict(getattr(user, "broker_credentials", {}) or {})
    entry: dict[str, Any] = {
        "connected_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    # 공통 필드
    if body.get("account_no"):
        entry["account_no"] = str(body["account_no"])
    if body.get("account_prod_cd"):
        entry["account_prod_cd"] = str(body["account_prod_cd"])
    # KIS 전용
    if body.get("appkey"):
        entry["appkey_enc"] = aes_encrypt(str(body["appkey"]))
    if body.get("appsecret"):
        entry["appsecret_enc"] = aes_encrypt(str(body["appsecret"]))
    # 키움/CREON 계좌 비밀번호 (선택)
    if body.get("account_password"):
        entry["account_password_enc"] = aes_encrypt(str(body["account_password"]))

    creds[chosen.value] = entry
    await db.execute(
        update(UserModel).where(UserModel.id == user.id).values(broker_credentials=creds)
    )
    await db.commit()
    # 응답에는 암호문 미노출
    return success_response(
        {
            "broker": chosen.value,
            "connected": True,
            "account_masked": (
                entry.get("account_no", "")[:2] + "****" + entry.get("account_no", "")[-2:]
                if entry.get("account_no")
                else None
            ),
        }
    )


@router.post("/brokers/{broker}/disconnect", summary="증권사 자격증명 삭제")
async def disconnect_broker(
    broker: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """해당 증권사의 자격증명을 삭제 (선호는 유지)."""
    from sqlalchemy import update

    from app.core.exceptions import AppException
    from app.domains.brokers import Broker
    from app.models.user import User as UserModel

    try:
        chosen = Broker(broker.upper())
    except ValueError:
        raise AppException("E0003", message="지원하지 않는 증권사입니다.")

    creds: dict[str, Any] = dict(getattr(user, "broker_credentials", {}) or {})
    creds.pop(chosen.value, None)
    await db.execute(
        update(UserModel).where(UserModel.id == user.id).values(broker_credentials=creds)
    )
    await db.commit()
    return success_response({"broker": chosen.value, "connected": False})


@router.post("/notifications/kakao/optin", summary="카카오 알림톡 수신 동의")
async def kakao_optin(
    payload: KakaoOptInIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """카카오 알림톡 수신 동의 + 전화번호 등록.

    - 카카오 비즈메시지 정책상 명시적 옵트인 필요.
    - 전화번호는 ``tp_user.users.phone`` 컬럼에 저장.
    """
    from sqlalchemy import update

    from app.models.user import User

    digits = "".join(c for c in payload.phone if c.isdigit())
    if not digits or len(digits) < 9:
        from app.core.exceptions import AppException

        raise AppException("E0003", message="유효한 전화번호가 아닙니다.")

    await db.execute(update(User).where(User.id == user.id).values(phone=digits))

    # telegram_enabled 컬럼을 카카오 옵트인 동의로 재사용 (스키마 호환)
    svc = NotificationService(db)
    await svc.update_channels(user.id, telegram_enabled=payload.consent)
    await db.commit()
    return success_response(
        {
            "consent": payload.consent,
            "phone": digits[:3] + "****" + digits[-4:] if len(digits) >= 7 else "***",
        }
    )
