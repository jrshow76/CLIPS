"""정리(cleanup) 태스크.

- SEC-004(GATE-3) : 만료된 refresh 세션 정리 (매일 04:00 KST)
- Redis 디버그 키(otp:debug:*, pwreset:*) 정리 등 후속 확장 가능

Beat 등록은 `app.workers.celery_app` 에서 한다.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


# 보관 기간: 만료일 이후 7일까지는 디버깅/감사 목적으로 보존
SESSION_RETENTION_DAYS = 7


@shared_task(name="cleanup.refresh_sessions", queue="default")
def cleanup_refresh_sessions() -> dict[str, Any]:
    """만료된 refresh 세션 정리.

    SEC-004(GATE-3): `expires_at < now - 7일` 인 행을 삭제하여 sessions 테이블 비대를 방지.
    회전 체인(`replaced_by_jti`)이 남아 있어도 만료된 행은 보안상 위험이 없으므로 안전.
    """
    async def _run() -> dict[str, Any]:
        from app.core.database import AsyncSessionLocal
        from app.repositories.user_repository import SessionRepository

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=SESSION_RETENTION_DAYS)
        async with AsyncSessionLocal() as db:
            repo = SessionRepository(db)
            deleted = await repo.delete_expired(cutoff)
            await db.commit()
            return {"deleted": deleted, "cutoff": cutoff.isoformat()}

    try:
        result = asyncio.run(_run())
        log.info("refresh_sessions_cleanup_done", **result)
        return result
    except Exception as e:  # noqa: BLE001
        log.exception("refresh_sessions_cleanup_error", error=str(e))
        return {"deleted": 0, "error": str(e)[:200]}
