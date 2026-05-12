"""전략 도메인 서비스."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import decode_jwt_token
from app.models.trade import Strategy
from app.models.user import User
from app.repositories.strategy_repository import StrategyRepository

log = structlog.get_logger(__name__)


class StrategyService:
    """전략 CRUD + 활성/비활성."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = StrategyRepository(db)

    async def list_for_user(
        self, user_id: int, *, active: bool | None, offset: int, limit: int
    ) -> tuple[list[Strategy], int]:
        return await self.repo.list_for_user(user_id, active=active, offset=offset, limit=limit)

    async def get_for_user(self, user_id: int, public_id: str) -> Strategy:
        s = await self.repo.find_by_public_id(public_id)
        if not s or s.user_id != user_id:
            raise AppException("E0062", message="전략을 찾을 수 없습니다.")
        return s

    async def create(
        self,
        *,
        user_id: int,
        name: str,
        description: str | None,
        entry_rules: dict[str, Any],
        exit_rules: dict[str, Any],
        universe: list[Any],
        limits: dict[str, Any],
    ) -> Strategy:
        self._validate_rules(entry_rules, exit_rules)
        s = Strategy(
            user_id=user_id,
            name=name,
            description=description,
            entry_rules=entry_rules,
            exit_rules=exit_rules,
            universe=universe,
            limits=limits,
            active=False,
        )
        await self.repo.add(s)
        await self.db.commit()
        await self.db.refresh(s)
        log.info("strategy_created", user_id=user_id, strategy_id=s.id)
        return s

    async def update(
        self,
        *,
        user_id: int,
        public_id: str,
        name: str | None = None,
        description: str | None = None,
        entry_rules: dict[str, Any] | None = None,
        exit_rules: dict[str, Any] | None = None,
        universe: list[Any] | None = None,
        limits: dict[str, Any] | None = None,
    ) -> Strategy:
        s = await self.get_for_user(user_id, public_id)
        if name is not None:
            s.name = name
        if description is not None:
            s.description = description
        if entry_rules is not None:
            s.entry_rules = entry_rules
        if exit_rules is not None:
            s.exit_rules = exit_rules
        if universe is not None:
            s.universe = universe
        if limits is not None:
            s.limits = limits
        self._validate_rules(s.entry_rules or {}, s.exit_rules or {})
        await self.db.commit()
        await self.db.refresh(s)
        return s

    async def delete(self, *, user_id: int, public_id: str) -> None:
        s = await self.get_for_user(user_id, public_id)
        if s.active:
            raise AppException("E0003", details={"active": ["활성 전략은 삭제할 수 없습니다."]})
        s.deleted_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        log.info("strategy_deleted", user_id=user_id, strategy_id=s.id)

    async def activate(
        self,
        *,
        user: User,
        public_id: str,
        active: bool,
        otp_token: str | None = None,
    ) -> Strategy:
        """전략 활성/비활성 토글.

        - LIVE 모드 사용자가 활성화 시 OTP 토큰 검증 필요.
        - 매매모드 검증: SIM 사용자는 즉시 활성화 허용.
        """
        s = await self.get_for_user(user.id, public_id)

        if active:
            # LIVE 모드 전환 시 추가 검증
            if user.trade_mode == "LIVE":
                if not otp_token:
                    raise AppException(
                        "E0011",
                        message="LIVE 모드 전략 활성화는 OTP 인증이 필요합니다.",
                    )
                try:
                    payload = decode_jwt_token(otp_token, expected_type="access")
                    if payload.get("role") != "ROLE_OTP":
                        raise ValueError("invalid otp token")
                except Exception as e:
                    raise AppException(
                        "E0011", message="OTP 토큰이 유효하지 않습니다."
                    ) from e
            s.active = True
            s.activated_at = datetime.now(tz=timezone.utc)
        else:
            s.active = False
            s.deactivated_at = datetime.now(tz=timezone.utc)

        await self.db.commit()
        await self.db.refresh(s)
        log.info(
            "strategy_activation_changed",
            user_id=user.id,
            strategy_id=s.id,
            active=active,
        )
        return s

    # ------------------------------------------------------------------
    # 내부 도우미
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_rules(entry: dict[str, Any], exit_rules: dict[str, Any]) -> None:
        """엔트리/엑시트 룰의 기본 구조 검증.

        룰 DSL 예: `{ "all": [{"indicator":"RSI", "op":"<", "value":30}, ...] }`
        """
        errors: dict[str, list[str]] = {}
        for field, rule in (("entry_rules", entry), ("exit_rules", exit_rules)):
            if not isinstance(rule, dict):
                errors[field] = ["객체 형태여야 합니다."]
                continue
            if rule and not any(k in rule for k in ("all", "any", "indicator")):
                errors[field] = ["all/any/indicator 키 중 하나가 필요합니다."]
        if errors:
            raise AppException("E0003", details=errors)
