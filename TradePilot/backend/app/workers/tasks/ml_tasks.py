"""ML 워커 태스크.

v1.0은 LSTM 학습/추론을 mock으로 처리한다. (실제 학습은 향후 BackendSenior가 LSTM 파이프라인을 구현)
"""
from __future__ import annotations

from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


# 메모리 기반 잡 상태 캐시 (운영 환경에서는 Redis로 대체)
_JOB_CACHE: dict[str, dict[str, Any]] = {}


@shared_task(name="ml.retrain", queue="ml", bind=True)
def retrain_lstm(self, job_id: str, codes: list[str], full: bool) -> dict[str, Any]:
    """LSTM 모델 재학습 (mock)."""
    log.info("ml_retrain_started", job_id=job_id, full=full, codes=codes)
    _JOB_CACHE[job_id] = {"status": "RUNNING"}

    # mock: 즉시 완료
    _JOB_CACHE[job_id] = {"status": "DONE"}
    log.info("ml_retrain_done", job_id=job_id)
    return {"job_id": job_id, "status": "DONE", "codes": codes, "full": full}


def get_job_status(job_id: str) -> dict[str, Any]:
    """학습 잡 상태 조회."""
    return _JOB_CACHE.get(job_id, {"status": "UNKNOWN"})
