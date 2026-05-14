"""알림 룰 엔진.

``tp_notify.alert_rules`` 에 등록된 사용자별 룰을 평가하여 트리거 발생 시
NotificationService 를 통해 알림을 발송한다.

지원 룰 타입 (event_type):
- ``PRICE_REACH``: 가격 도달
    condition: {"stock_code": str, "op": "GTE"|"LTE", "price": number}
- ``RSI_THRESHOLD``: RSI 임계
    condition: {"stock_code": str, "period": int=14, "op": "GTE"|"LTE", "value": number}
- ``PNL_THRESHOLD``: 손익률 임계
    condition: {"op": "GTE"|"LTE", "value_pct": number}
- ``DAILY_LOSS``: 일일 손실 한도
    condition: {"pct": number}  (예: -3.0)

룰 평가는 시그널/포트폴리오/체결 이벤트가 발생할 때 트리거된다(외부 호출).
v1은 단순 비교 연산만 지원하며, 추후 DSL(``app.domains.rules.evaluator``)로 확장.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import AlertRule
from app.models.user import User
from app.services.notification_service import NotificationService

log = structlog.get_logger(__name__)


class AlertRuleEngine:
    """알림 룰 평가/발화."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.noti_svc = NotificationService(db)

    # ------------------------------------------------------------------
    # 조회
    # ------------------------------------------------------------------
    async def list_rules(
        self,
        *,
        user_id: int,
        event_types: Iterable[str] | None = None,
        only_active: bool = True,
    ) -> list[AlertRule]:
        stmt = select(AlertRule).where(AlertRule.user_id == user_id)
        if only_active:
            stmt = stmt.where(AlertRule.active.is_(True))
        if event_types:
            stmt = stmt.where(AlertRule.event_type.in_(list(event_types)))
        return list((await self.db.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------
    # 트리거 진입점
    # ------------------------------------------------------------------
    async def on_price_tick(
        self,
        *,
        user: User,
        stock_code: str,
        stock_name: str,
        price: Decimal | float,
    ) -> int:
        """가격 틱 이벤트로 PRICE_REACH 룰 평가."""
        rules = await self.list_rules(user_id=user.id, event_types=["PRICE_REACH"])
        fired = 0
        price_num = float(price)
        for r in rules:
            cond = r.condition or {}
            if str(cond.get("stock_code") or "") != stock_code:
                continue
            if _compare(price_num, cond.get("op", "GTE"), float(cond.get("price", 0))):
                await self.noti_svc.send_signal_alert(
                    user=user,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    action="ALERT",
                    rule_code="PRICE_REACH",
                    confidence=r.priority,
                    trigger_price=str(price),
                    strategy_name="가격 알림",
                )
                fired += 1
        return fired

    async def on_signal_event(
        self,
        *,
        user: User,
        signal: dict[str, Any],
    ) -> int:
        """시그널 생성 이벤트로 RSI/MACD 등 신뢰도 기반 룰 평가.

        condition 예: {"min_confidence": "HIGH"}
        """
        rules = await self.list_rules(user_id=user.id, event_types=["SIGNAL"])
        fired = 0
        order = {"LOW": 0, "MID": 1, "HIGH": 2}
        sig_conf = str(signal.get("confidence", "LOW")).upper()
        for r in rules:
            cond = r.condition or {}
            min_conf = str(cond.get("min_confidence", "LOW")).upper()
            if order.get(sig_conf, 0) < order.get(min_conf, 0):
                continue
            await self.noti_svc.send_signal_alert(
                user=user,
                stock_code=str(signal.get("stock_code", "")),
                stock_name=str(signal.get("stock_name", "")),
                action=str(signal.get("action", "BUY")),
                rule_code=str(signal.get("code", "")),
                confidence=sig_conf,
                trigger_price=str(signal.get("trigger_price", "0")),
                strategy_name=str(signal.get("strategy_name", "사용자 룰")),
            )
            fired += 1
        return fired

    async def on_pnl_update(
        self,
        *,
        user: User,
        pnl_pct: float,
    ) -> int:
        """손익률 갱신 이벤트로 PNL_THRESHOLD / DAILY_LOSS 평가."""
        rules = await self.list_rules(
            user_id=user.id, event_types=["PNL_THRESHOLD", "DAILY_LOSS"]
        )
        fired = 0
        for r in rules:
            cond = r.condition or {}
            if r.event_type == "PNL_THRESHOLD":
                if _compare(pnl_pct, cond.get("op", "LTE"), float(cond.get("value_pct", 0))):
                    await self.noti_svc.notify_user(
                        user_id=user.id,
                        user_public_id=str(user.public_id),
                        title=f"[손익 알림] {pnl_pct:+.2f}%",
                        body=f"포트폴리오 손익률이 임계값을 도달했습니다: {pnl_pct:+.2f}%",
                        event_type="PNL_THRESHOLD",
                        severity="WARN",
                        payload={"pnl_pct": pnl_pct, "condition": cond},
                    )
                    fired += 1
            elif r.event_type == "DAILY_LOSS":
                threshold = float(cond.get("pct", -3.0))
                if pnl_pct <= threshold:
                    await self.noti_svc.notify_user(
                        user_id=user.id,
                        user_public_id=str(user.public_id),
                        title="[중요] 일일 손실 한도 도달",
                        body=f"일일 손실 {pnl_pct:+.2f}% 가 한도({threshold:+.2f}%) 에 도달했습니다.",
                        event_type="DAILY_LOSS",
                        severity="CRITICAL",
                        payload={"pnl_pct": pnl_pct, "threshold_pct": threshold},
                    )
                    fired += 1
        return fired


def _compare(left: float, op: str, right: float) -> bool:
    """간단 비교 연산자."""
    op_upper = str(op).upper()
    if op_upper == "GTE":
        return left >= right
    if op_upper == "LTE":
        return left <= right
    if op_upper == "GT":
        return left > right
    if op_upper == "LT":
        return left < right
    if op_upper == "EQ":
        return left == right
    log.warning("alert_rule_unknown_op", op=op)
    return False
