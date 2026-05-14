"""주문 후처리 태스크.

- 실시간 체결 이벤트 수신 (`tp:account.execution`) → DB 반영
- 주문 상태 변경 (`tp:account.order_update`) → 상태 동기화
- LIVE 모드의 비동기 체결 갱신
- **SEC-003(GATE-1)**: Kill Switch 부분 실패 재시도 (5분 주기)
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(name="orders.handle_execution", queue="orders")
def handle_execution(payload: dict[str, Any]) -> dict[str, Any]:
    """게이트웨이 체결 이벤트 → DB 반영.

    실제 구현: 본 페이로드의 broker_order_no 또는 order_id로 Order/Fill 행 갱신,
    포지션/잔고 재계산, WebSocket 푸시.
    """
    log.info("execution_handled", payload=payload)
    return {"received": True}


@shared_task(name="orders.handle_order_update", queue="orders")
def handle_order_update(payload: dict[str, Any]) -> dict[str, Any]:
    """주문 상태 변경 이벤트 처리."""
    log.info("order_update_handled", payload=payload)
    return {"received": True}


@shared_task(name="orders.kill_switch_retry", queue="orders")
def kill_switch_retry() -> dict[str, Any]:
    """Kill Switch 부분 실패 재시도 (5분 주기 Beat).

    `last_kill_switch_attempt_at IS NOT NULL` 이고 여전히 활성 상태인 주문에
    대해 라우터의 cancel_order를 재호출한다. 5회 이상 시도된 주문은 제외하여
    무한 루프를 방지하고, 운영자가 수동 처리하도록 알림(SEC-003 후속).
    """
    async def _run() -> dict[str, Any]:
        from app.core.database import AsyncSessionLocal
        from app.services.kill_switch_service import KillSwitchService

        async with AsyncSessionLocal() as session:
            svc = KillSwitchService(session)
            return await svc.retry_failed_cancels(max_orders=50, max_attempts=5)

    try:
        result = asyncio.run(_run())
        log.info("kill_switch_retry_done", **result)
        return result
    except Exception as e:  # noqa: BLE001
        log.exception("kill_switch_retry_error", error=str(e))
        return {"retried": 0, "canceled": 0, "still_failed": 0, "error": str(e)[:200]}
