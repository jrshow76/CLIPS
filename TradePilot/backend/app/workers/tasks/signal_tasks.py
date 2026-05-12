"""시그널 생성 배치 태스크.

스케줄: 평일 09:00~15:20, 5초 간격 (APScheduler가 enqueue).
"""
from __future__ import annotations

from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(name="signals.evaluate", bind=True, max_retries=3, queue="signals")
def evaluate(self: Any, user_id: int | None = None) -> dict[str, Any]:
    """시그널 평가 진입점.

    실제 구현: 사용자 활성 전략 → universe 종목 캔들 로딩 → SignalService.evaluate_rules
    → 신규 시그널 DB insert → WebSocket push.
    """
    log.info("signal_eval_start", user_id=user_id)
    try:
        # placeholder
        return {"user_id": user_id, "generated": 0}
    except Exception as e:
        log.exception("signal_eval_failed")
        raise self.retry(exc=e, countdown=10)
