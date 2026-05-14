"""설정 API 라우터.

`docs/13_api_requirements.md` §15 명세 구현.
모드 전환, 한도 조회/수정, Kill Switch, 크레온 상태, 스케줄.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, TradeModeDep
from app.core.response import success_response
from app.schemas.settings import (
    CreonStatusOut,
    CreonTestIn,
    KillSwitchIn,
    RiskLimitOut,
    RiskLimitUpdateIn,
    ScheduleOut,
    ScheduleUpdateIn,
    TradeModeOut,
    TradeModeSwitchIn,
)
from app.services.kill_switch_service import KillSwitchService
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
