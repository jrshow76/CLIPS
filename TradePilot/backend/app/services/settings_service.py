"""설정/한도/모드 전환 서비스.

BackendSenior의 TradeLimitService / KillSwitchService 와 호환되도록 구성한다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import decode_jwt_token
from app.models.trade import TradeLimit
from app.models.user import User, UserSettings
from app.repositories.order_repository import TradeLimitRepository
from app.repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)


class SettingsService:
    """설정 도메인 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.limits = TradeLimitRepository(db)

    # ------------------------------------------------------------------
    # 매매 모드
    # ------------------------------------------------------------------
    async def get_trade_mode(self, user: User) -> dict[str, Any]:
        return {"mode": user.trade_mode, "switched_at": user.updated_at}

    async def switch_trade_mode(
        self,
        *,
        user: User,
        target: str,
        otp_token: str | None,
        terms_token: str | None,
    ) -> dict[str, Any]:
        """SIM ↔ LIVE 전환.

        LIVE 전환 게이트(간소화):
        1) 약관 동의 (`disclaimer_agreed_at` 또는 terms_token 제시)
        2) OTP 검증 토큰 (ROLE_OTP 클레임)
        3) 권한: ROLE_TRADER_PRO 또는 ROLE_ADMIN
        """
        target = target.upper()
        if target not in ("SIM", "LIVE"):
            raise AppException("E0003", details={"target": ["SIM 또는 LIVE"]})
        if user.trade_mode == target:
            return {"mode": user.trade_mode, "switched_at": user.updated_at}

        if target == "LIVE":
            # 권한
            if user.role not in ("ROLE_TRADER_PRO", "ROLE_ADMIN"):
                raise AppException("E0016", message="LIVE 권한이 없습니다.")
            # 약관 동의
            if not user.disclaimer_agreed_at and not terms_token:
                raise AppException("E0013", message="약관 동의가 필요합니다.")
            # OTP
            if not otp_token:
                raise AppException("E0011", message="OTP 검증 토큰이 필요합니다.")
            try:
                payload = decode_jwt_token(otp_token, expected_type="access")
                if payload.get("role") != "ROLE_OTP":
                    raise ValueError("invalid otp token")
            except Exception as e:
                raise AppException("E0011", message="OTP 토큰이 유효하지 않습니다.") from e

        user.trade_mode = target
        if target == "LIVE" and terms_token and not user.disclaimer_agreed_at:
            user.disclaimer_agreed_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)
        log.info("trade_mode_switched", user_id=user.id, mode=target)
        return {"mode": user.trade_mode, "switched_at": user.updated_at}

    # ------------------------------------------------------------------
    # 한도 (risk-limits)
    # ------------------------------------------------------------------
    async def get_limits(self, user_id: int) -> TradeLimit:
        return await self.limits.find_or_default(user_id)

    async def update_limits(self, user_id: int, **patch: Any) -> TradeLimit:
        limits = await self.limits.find_or_default(user_id)
        for k, v in patch.items():
            if v is None:
                continue
            if hasattr(limits, k):
                setattr(limits, k, v)
        await self.db.commit()
        await self.db.refresh(limits)
        log.info("risk_limits_updated", user_id=user_id, patch=list(patch.keys()))
        return limits

    # ------------------------------------------------------------------
    # 크레온 상태/테스트 (mock)
    # ------------------------------------------------------------------
    async def get_creon_status(self, user_id: int) -> dict[str, Any]:
        return {
            "connected": False,
            "account_masked": "8****1234",
            "last_check_at": datetime.now(tz=timezone.utc),
        }

    async def test_creon(self, user_id: int, password_token: str) -> dict[str, Any]:
        if not password_token:
            raise AppException("E0012", message="크레온 인증 토큰이 필요합니다.")
        # 실제 연결 테스트는 LiveOrderRouter 게이트웨이 통한 핑 - v1은 mock
        return {"connected": True, "checked_at": datetime.now(tz=timezone.utc).isoformat()}

    # ------------------------------------------------------------------
    # 스케줄 (UserSettings.schedule JSONB 활용)
    # ------------------------------------------------------------------
    async def get_schedule(self, user_id: int) -> dict[str, Any]:
        s = await self.db.get(UserSettings, user_id)
        if not s:
            s = UserSettings(user_id=user_id)
            self.db.add(s)
            await self.db.commit()
            await self.db.refresh(s)
        return s.schedule or {
            "market_hours_only": True,
            "pre_market_start": "08:30",
            "post_market_end": "16:00",
            "auto_kill_switch_loss_pct": None,
        }

    async def update_schedule(self, user_id: int, **patch: Any) -> dict[str, Any]:
        s = await self.db.get(UserSettings, user_id)
        if not s:
            s = UserSettings(user_id=user_id)
            self.db.add(s)
            await self.db.flush()
        current = dict(s.schedule or {})
        for k, v in patch.items():
            if v is not None:
                current[k] = v if not isinstance(v, Decimal) else float(v)
        s.schedule = current
        await self.db.commit()
        return current
