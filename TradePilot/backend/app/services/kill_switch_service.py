"""Kill Switch 서비스.

`docs/14_exception_policy.md` §8 비상정지 처리 흐름:
1. 활성 전략 일괄 비활성화
2. 진행 중 주문 전체 취소
3. 모드 강제 SIM 전환
4. 감사 로그 기록
5. 인앱/이메일 알림
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.domains.enums import OrderStatus
from app.models.trade import KillSwitchLog, Order, Strategy
from app.models.user import User
from app.repositories.order_repository import OrderRepository

log = structlog.get_logger(__name__)


class KillSwitchService:
    """비상정지 처리."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)

    async def trigger(
        self,
        *,
        user_id: int,
        trade_mode: str,
        trigger_type: str = "USER",
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Kill Switch 발동.

        반환: {canceled_orders, failed, mode_switched}
        """
        log.warning(
            "kill_switch_triggered",
            user_id=user_id,
            trade_mode=trade_mode,
            trigger_type=trigger_type,
            reason=reason,
        )

        # 1) 활성 전략 일괄 비활성화
        await self.db.execute(
            update(Strategy)
            .where(Strategy.user_id == user_id, Strategy.active.is_(True))
            .values(active=False, deactivated_at=datetime.now(tz=timezone.utc))
        )

        # 2) 미체결 주문 일괄 취소
        canceled: list[str] = []
        failed: list[dict[str, Any]] = []
        from sqlalchemy import select
        from app.models.trade import Order as OrderModel

        active_statuses = ["NEW", "PARTIAL", "PENDING", "ACCEPTED"]
        stmt = select(OrderModel).where(
            OrderModel.user_id == user_id,
            OrderModel.trade_mode == trade_mode,
            OrderModel.status.in_(active_statuses),
        )
        orders = (await self.db.execute(stmt)).scalars().all()
        now = datetime.now(tz=timezone.utc)
        for o in orders:
            try:
                # SIM 모드는 즉시 취소 (LIVE 모드는 게이트웨이 호출이 필요하나, 본 메서드에서는
                # 일단 DB만 정리하고 외부 취소는 별도 처리/재시도 큐로 위임)
                o.status = OrderStatus.CANCELED.value
                o.canceled_at = now
                canceled.append(str(o.public_id))
            except Exception as e:
                failed.append({"order_id": str(o.public_id), "error": str(e)})

        # 3) 모드 강제 SIM 전환 (LIVE → SIM)
        mode_switched = False
        if trade_mode == "LIVE":
            await self.db.execute(
                update(User).where(User.id == user_id).values(trade_mode="SIM")
            )
            mode_switched = True

        # 4) 감사 로그
        ks_log = KillSwitchLog(
            user_id=user_id,
            trigger_type=trigger_type,
            reason=reason,
            canceled_count=len(canceled),
            failed_count=len(failed),
            detail={"canceled": canceled, "failed": failed},
        )
        self.db.add(ks_log)

        await self.db.commit()

        result = {
            "canceled_orders": canceled,
            "failed": failed,
            "mode_switched": mode_switched,
        }

        if failed:
            log.warning("kill_switch_partial_failure", failed=failed)
            # 부분 실패 시 E0015 (호출자에 정보 포함하여 반환)
            raise AppException(
                "E0015",
                message="비상정지 처리 중 일부 실패가 발생했습니다.",
                details=result,
            )
        return result
