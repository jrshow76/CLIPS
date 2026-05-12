"""주문 후처리 태스크.

- 실시간 체결 이벤트 수신 (`tp:account.execution`) → DB 반영
- 주문 상태 변경 (`tp:account.order_update`) → 상태 동기화
- LIVE 모드의 비동기 체결 갱신
"""
from __future__ import annotations

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
