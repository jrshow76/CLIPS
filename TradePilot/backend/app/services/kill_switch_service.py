"""Kill Switch 서비스.

`docs/14_exception_policy.md` §8 비상정지 처리 흐름:
1. 활성 전략 일괄 비활성화
2. 진행 중 주문 전체 취소  → **SEC-003(GATE-1)**: 라우터(SIM/LIVE) 통한 실제 cancel_order 호출
3. 모드 강제 SIM 전환
4. 감사 로그 기록 (canceled/failed/duration)
5. 인앱/이메일 알림
6. 부분 실패 시 ``last_kill_switch_attempt_at`` / ``kill_switch_attempts`` 기록 → 재시도 워커가 5분 주기로 재호출

SLA: 전체 절차 5초 이내 응답 (게이트웨이 호출 2초 + 안전 마진).
초과 시 처리 중단 → 부분 결과 즉시 반환 + ``tp:gateway.killswitch_partial`` Redis publish.

자동 트리거 (호출자는 ``trigger_source`` 인자로 구분):
- USER       : 사용자 수동
- DAILY_LOSS : 일일 손실 -3% 도달
- CREON_DISCONNECT : 게이트웨이 60초 이상 응답 없음
- STOP_LOSS  : 동일 종목 5회 이상 실패
- SYSTEM     : 운영자 비상정지
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import orjson
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.redis_client import get_redis
from app.domains.enums import OrderStatus, TradeMode
from app.integrations.factory import get_order_router
from app.models.market import Stock
from app.models.trade import KillSwitchLog, Order, Strategy
from app.models.user import User
from app.repositories.order_repository import OrderRepository

log = structlog.get_logger(__name__)


# SLA 상수
KILL_SWITCH_SLA_SEC = 5.0
GATEWAY_CANCEL_TIMEOUT_SEC = 2.0

# 활성 상태 (cancel 대상)
_ACTIVE_STATUSES: tuple[str, ...] = ("NEW", "PENDING", "PARTIAL", "ACCEPTED")


class KillSwitchService:
    """비상정지 처리."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)

    # ------------------------------------------------------------------
    # 진입점 (라우터/스케줄러 양쪽에서 호출)
    # ------------------------------------------------------------------
    async def trigger(
        self,
        *,
        user_id: int,
        trade_mode: str,
        trigger_type: str = "USER",
        trigger_source: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Kill Switch 발동.

        `trigger_source`는 호환을 위해 도입했으며 미지정 시 `trigger_type`을 사용한다.

        반환:
        - canceled_orders: 취소 성공한 주문 public_id 리스트
        - failed: [{order_id, error, attempts}] 부분 실패 목록
        - mode_switched: LIVE → SIM 강제 전환 여부
        - duration_ms: 전체 절차 소요 시간
        - sla_violated: 5초 SLA 초과 여부
        """
        started_at = time.monotonic()
        source = (trigger_source or trigger_type or "USER").upper()
        log.warning(
            "kill_switch_triggered",
            user_id=user_id,
            trade_mode=trade_mode,
            trigger_type=trigger_type,
            trigger_source=source,
            reason=reason,
        )

        # 1) 활성 전략 일괄 비활성화
        await self.db.execute(
            update(Strategy)
            .where(Strategy.user_id == user_id, Strategy.active.is_(True))
            .values(active=False, deactivated_at=datetime.now(tz=timezone.utc))
        )

        # 2) 미체결 주문 조회
        stmt = select(Order).where(
            Order.user_id == user_id,
            Order.trade_mode == trade_mode,
            Order.status.in_(_ACTIVE_STATUSES),
        )
        active_orders = list((await self.db.execute(stmt)).scalars().all())

        # 3) 라우터를 통해 cancel_order 호출 (SLA 5초 회로차단)
        canceled, failed, sla_violated = await self._cancel_all_with_sla(
            orders=active_orders,
            trade_mode=trade_mode,
            started_at=started_at,
        )

        # 4) trade_mode → SIM 강제 전환 (LIVE인 경우)
        mode_switched = False
        if trade_mode == TradeMode.LIVE.value:
            await self.db.execute(
                update(User).where(User.id == user_id).values(trade_mode="SIM")
            )
            mode_switched = True

        # 5) 감사 로그 기록
        duration_ms = int((time.monotonic() - started_at) * 1000)
        # KillSwitchLog.trigger_type CHECK 제약: USER/DAILY_LOSS/CREON_DISCONNECT/SYSTEM/STOP_LOSS/MAINTENANCE
        # 외부 호출에서 임의 값이 들어와도 안전하도록 화이트리스트 매핑.
        log_type = source if source in (
            "USER", "DAILY_LOSS", "CREON_DISCONNECT", "SYSTEM", "STOP_LOSS", "MAINTENANCE"
        ) else "USER"
        ks_log = KillSwitchLog(
            user_id=user_id,
            trigger_type=log_type,
            reason=reason,
            canceled_count=len(canceled),
            failed_count=len(failed),
            detail={
                "canceled": canceled,
                "failed": failed,
                "duration_ms": duration_ms,
                "sla_violated": sla_violated,
                "trade_mode": trade_mode,
                "trigger_source": source,
            },
        )
        self.db.add(ks_log)
        await self.db.commit()

        # 6) SLA 초과 또는 부분 실패 → Redis 이벤트 publish (호출자 응답 차단 방지)
        if sla_violated or failed:
            await self._publish_partial_event(
                user_id=user_id,
                trade_mode=trade_mode,
                canceled=canceled,
                failed=failed,
                duration_ms=duration_ms,
                sla_violated=sla_violated,
                trigger_source=source,
                reason=reason,
            )

        result: dict[str, Any] = {
            "canceled_orders": canceled,
            "failed": failed,
            "mode_switched": mode_switched,
            "duration_ms": duration_ms,
            "sla_violated": sla_violated,
        }

        if failed:
            log.warning(
                "kill_switch_partial_failure",
                user_id=user_id,
                failed_count=len(failed),
                sla_violated=sla_violated,
            )
            raise AppException(
                "E0015",
                message="비상정지 처리 중 일부 실패가 발생했습니다.",
                details=result,
            )
        return result

    # ------------------------------------------------------------------
    # 내부: cancel_all + SLA
    # ------------------------------------------------------------------
    async def _cancel_all_with_sla(
        self,
        *,
        orders: list[Order],
        trade_mode: str,
        started_at: float,
    ) -> tuple[list[str], list[dict[str, Any]], bool]:
        """주문 목록을 라우터로 취소. SLA 5초 회로차단.

        반환: (canceled[public_id], failed[{order_id,error,attempts}], sla_violated)
        """
        canceled: list[str] = []
        failed: list[dict[str, Any]] = []
        sla_violated = False
        router = get_order_router(trade_mode)
        now = datetime.now(tz=timezone.utc)

        # 종목코드 사전 조회 (LIVE cancel에 stock_code 필요)
        stock_ids = {o.stock_id for o in orders}
        stock_map: dict[int, str] = {}
        if stock_ids:
            stmt = select(Stock).where(Stock.id.in_(stock_ids))
            for s in (await self.db.execute(stmt)).scalars().all():
                stock_map[s.id] = s.code

        for o in orders:
            # SLA 체크: 남은 시간이 게이트웨이 타임아웃보다 짧으면 중단
            elapsed = time.monotonic() - started_at
            remaining = KILL_SWITCH_SLA_SEC - elapsed
            if remaining <= 0.2:  # 200ms 안전 마진
                sla_violated = True
                log.warning(
                    "kill_switch_sla_breached",
                    elapsed_sec=elapsed,
                    remaining_orders=len(orders) - (len(canceled) + len(failed)),
                )
                # 남은 주문은 모두 failed로 기록 (재시도 워커가 처리)
                o.kill_switch_attempts = (o.kill_switch_attempts or 0) + 1
                o.last_kill_switch_attempt_at = now
                failed.append(
                    {
                        "order_id": str(o.public_id),
                        "error": "kill_switch_sla_exceeded",
                        "attempts": o.kill_switch_attempts,
                    }
                )
                continue

            # 타임아웃: 게이트웨이 2초 vs SLA 남은 시간 중 작은 값
            timeout = min(GATEWAY_CANCEL_TIMEOUT_SEC, max(0.5, remaining - 0.2))
            stock_code = stock_map.get(o.stock_id, "")
            # X-Idempotency-Key: kill switch + order_id (재시도 동일 키)
            idem_key = f"killswitch:{o.id}:{trade_mode}"

            try:
                # 라우터 cancel_order에 위임 (SIM은 in-memory, LIVE는 게이트웨이 HTTP)
                # 호출 자체에도 SLA 보호용 asyncio.wait_for 적용
                result = await asyncio.wait_for(
                    router.cancel_order(
                        o.id,
                        o.broker_order_no,
                        stock_code,
                        timeout_sec=timeout,
                        idempotency_key=idem_key,
                    ),
                    timeout=timeout + 0.3,  # 라우터 자체 타임아웃 + 마진
                )
            except (AppException, asyncio.TimeoutError, Exception) as e:  # noqa: BLE001
                # 실패 → kill_switch_attempts 증가 + DB는 그대로 (status 유지)
                o.kill_switch_attempts = (o.kill_switch_attempts or 0) + 1
                o.last_kill_switch_attempt_at = now
                err_msg = (
                    e.code if isinstance(e, AppException) else type(e).__name__
                )
                failed.append(
                    {
                        "order_id": str(o.public_id),
                        "error": err_msg,
                        "attempts": o.kill_switch_attempts,
                    }
                )
                log.warning(
                    "kill_switch_cancel_failed",
                    order_id=o.id,
                    error=str(e)[:200],
                )
                continue

            if result.accepted and result.status == OrderStatus.CANCELED.value:
                o.status = OrderStatus.CANCELED.value
                o.canceled_at = now
                o.broker_order_no = result.broker_order_no or o.broker_order_no
                # 성공 시 재시도 흔적은 남기지 않음
                o.kill_switch_attempts = (o.kill_switch_attempts or 0) + 1
                o.last_kill_switch_attempt_at = None
                canceled.append(str(o.public_id))
            else:
                o.kill_switch_attempts = (o.kill_switch_attempts or 0) + 1
                o.last_kill_switch_attempt_at = now
                failed.append(
                    {
                        "order_id": str(o.public_id),
                        "error": result.reject_reason or f"router_status={result.status}",
                        "attempts": o.kill_switch_attempts,
                    }
                )

        return canceled, failed, sla_violated

    # ------------------------------------------------------------------
    # 부분 실패 재시도 (백그라운드 워커에서 호출)
    # ------------------------------------------------------------------
    async def retry_failed_cancels(
        self,
        *,
        max_orders: int = 50,
        max_attempts: int = 5,
    ) -> dict[str, Any]:
        """``last_kill_switch_attempt_at IS NOT NULL`` 이고 여전히 활성 상태인 주문에
        대해 게이트웨이 cancel_order 재시도.

        호출 주체: ``orders.kill_switch_retry`` Celery 태스크 (5분 주기).
        """
        stmt = (
            select(Order)
            .where(
                Order.last_kill_switch_attempt_at.is_not(None),
                Order.status.in_(_ACTIVE_STATUSES),
                Order.kill_switch_attempts < max_attempts,
            )
            .order_by(Order.last_kill_switch_attempt_at.asc())
            .limit(max_orders)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        if not rows:
            return {"retried": 0, "canceled": 0, "still_failed": 0}

        # 모드별 그룹핑하여 라우터 재호출
        canceled = 0
        still_failed = 0
        stock_ids = {o.stock_id for o in rows}
        stock_map: dict[int, str] = {}
        if stock_ids:
            sstmt = select(Stock).where(Stock.id.in_(stock_ids))
            for s in (await self.db.execute(sstmt)).scalars().all():
                stock_map[s.id] = s.code

        now = datetime.now(tz=timezone.utc)
        for o in rows:
            router = get_order_router(o.trade_mode)
            try:
                result = await asyncio.wait_for(
                    router.cancel_order(
                        o.id,
                        o.broker_order_no,
                        stock_map.get(o.stock_id, ""),
                        timeout_sec=GATEWAY_CANCEL_TIMEOUT_SEC,
                        idempotency_key=f"killswitch:{o.id}:{o.trade_mode}",
                    ),
                    timeout=GATEWAY_CANCEL_TIMEOUT_SEC + 0.5,
                )
            except Exception as e:  # noqa: BLE001
                o.kill_switch_attempts = (o.kill_switch_attempts or 0) + 1
                o.last_kill_switch_attempt_at = now
                still_failed += 1
                log.warning(
                    "kill_switch_retry_failed",
                    order_id=o.id,
                    error=str(e)[:200],
                    attempts=o.kill_switch_attempts,
                )
                continue

            if result.accepted and result.status == OrderStatus.CANCELED.value:
                o.status = OrderStatus.CANCELED.value
                o.canceled_at = now
                o.kill_switch_attempts = (o.kill_switch_attempts or 0) + 1
                o.last_kill_switch_attempt_at = None
                canceled += 1
            else:
                o.kill_switch_attempts = (o.kill_switch_attempts or 0) + 1
                o.last_kill_switch_attempt_at = now
                still_failed += 1

        await self.db.commit()
        return {
            "retried": len(rows),
            "canceled": canceled,
            "still_failed": still_failed,
        }

    # ------------------------------------------------------------------
    # 보조 — Redis publish (부분 실패 / SLA 초과 알림)
    # ------------------------------------------------------------------
    async def _publish_partial_event(
        self,
        *,
        user_id: int,
        trade_mode: str,
        canceled: list[str],
        failed: list[dict[str, Any]],
        duration_ms: int,
        sla_violated: bool,
        trigger_source: str,
        reason: str | None,
    ) -> None:
        """``tp:gateway.killswitch_partial`` 채널에 부분 실패 이벤트 publish.

        - 실패 시 로그만 남기고 무시 (KillSwitch 흐름 차단 금지)
        - QA/운영 알림 채널이 본 이벤트를 구독하여 알림 발송
        """
        try:
            event = {
                "type": "killswitch_partial" if failed else "killswitch_sla_violated",
                "user_id": user_id,
                "trade_mode": trade_mode,
                "canceled_count": len(canceled),
                "failed_count": len(failed),
                "failed": failed,
                "duration_ms": duration_ms,
                "sla_violated": sla_violated,
                "trigger_source": trigger_source,
                "reason": reason,
                "event_id": uuid4().hex,
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }
            await get_redis().publish(
                "tp:gateway.killswitch_partial", orjson.dumps(event)
            )
        except Exception as e:  # noqa: BLE001
            log.warning("killswitch_publish_failed", error=str(e))
