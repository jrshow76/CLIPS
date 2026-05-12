"""시그널 관리 서비스 (조회/무시).

기존 `SignalService`는 룰 평가 + 신규 시그널 생성 책임이므로,
사용자 인터랙션(조회·무시·강제 평가)을 분리하여 본 서비스에서 다룬다.
"""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.analysis import Signal
from app.models.market import Stock
from app.repositories.signal_repository import SignalRepository

log = structlog.get_logger(__name__)


class SignalManagementService:
    """시그널 조회/관리."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SignalRepository(db)

    async def get_one(self, *, user_id: int, signal_public_id: str) -> tuple[Signal, Stock]:
        sig = await self.repo.find_by_public_id(signal_public_id)
        if not sig or sig.user_id != user_id:
            raise AppException("E0062", message="시그널을 찾을 수 없습니다.")
        stock = await self.db.get(Stock, sig.stock_id)
        if not stock:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")
        return sig, stock

    async def ignore(self, *, user_id: int, signal_public_id: str) -> Signal:
        sig = await self.repo.find_by_public_id(signal_public_id)
        if not sig or sig.user_id != user_id:
            raise AppException("E0062", message="시그널을 찾을 수 없습니다.")
        if sig.status not in ("ACTIVE",):
            raise AppException(
                "E0003",
                details={"status": [f"현재 상태({sig.status})에서 무시할 수 없습니다."]},
            )
        sig.status = "IGNORED"
        sig.ignored_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        log.info("signal_ignored", user_id=user_id, signal_id=sig.id)
        return sig

    async def count_summary(self, user_id: int) -> dict[str, int]:
        return await self.repo.count_summary(user_id)
