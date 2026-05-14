"""익스포트 워커 태스크.

큐: ``exports``

태스크:
    * ``exports.run`` - 단일 익스포트 실행
    * ``exports.cleanup_expired`` - 만료된 export_jobs + S3 객체 삭제 (매일 04:00 KST)

진행률 단계:
    10%(추출) → 60%(파일 생성) → 90%(S3 업로드) → 100%(완료)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# exports.run
# ---------------------------------------------------------------------------
@shared_task(
    name="exports.run",
    queue="exports",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
)
def run_export_task(self, job_id: int) -> dict[str, Any]:
    """단일 익스포트 실행 (boto3 + pandas 동기 작업이라 asyncio 래핑)."""
    log.info("export_run_started", job_id=job_id)
    try:
        result = asyncio.run(_run_async(job_id))
    except Exception as exc:  # noqa: BLE001
        log.exception("export_run_error", job_id=job_id, error=str(exc))
        # 비즈니스 오류는 runner 내부에서 FAILED 마킹하므로
        # 여기서는 인프라 오류(예: DB 연결 실패) 등을 재시도한다.
        raise self.retry(exc=exc)
    log.info("export_run_finished", job_id=job_id, status=result.get("status"))
    return result


async def _run_async(job_id: int) -> dict[str, Any]:
    from app.core.database import AsyncSessionLocal
    from app.services.export_engine.runner import run_export

    async with AsyncSessionLocal() as db:
        result = await run_export(db, job_id)
        return {
            "job_id": job_id,
            "status": result.status,
            "row_count": result.row_count,
            "file_size_bytes": result.file_size_bytes,
            "error": result.error_message,
        }


# ---------------------------------------------------------------------------
# exports.cleanup_expired
# ---------------------------------------------------------------------------
@shared_task(name="exports.cleanup_expired", queue="default")
def cleanup_expired_exports() -> dict[str, Any]:
    """만료된 export_jobs 의 S3 객체 + DB 행 정리.

    조건: ``expires_at < now()`` 이고 ``status IN ('DONE','EXPIRED','FAILED','CANCELED')``.
    S3 삭제 실패는 best-effort (warn 로깅 후 진행).
    """
    try:
        result = asyncio.run(_cleanup_async())
        log.info("exports_cleanup_done", **result)
        return result
    except Exception as exc:  # noqa: BLE001
        log.exception("exports_cleanup_error", error=str(exc))
        return {"deleted": 0, "error": str(exc)[:200]}


async def _cleanup_async() -> dict[str, Any]:
    from sqlalchemy import and_, select

    from app.core.database import AsyncSessionLocal
    from app.models.trade import ExportJob
    from app.services.export_engine.s3_uploader import S3Uploader

    uploader = S3Uploader()
    deleted_db = 0
    deleted_s3 = 0
    now = datetime.now(tz=timezone.utc)

    async with AsyncSessionLocal() as db:
        stmt = select(ExportJob).where(
            and_(
                ExportJob.expires_at.is_not(None),
                ExportJob.expires_at < now,
                ExportJob.status.in_(["DONE", "EXPIRED", "FAILED", "CANCELED"]),
            )
        )
        rows = list((await db.execute(stmt)).scalars().all())
        for job in rows:
            if job.file_path:
                try:
                    uploader.delete_object(job.file_path)
                    deleted_s3 += 1
                except Exception:  # noqa: BLE001 - best effort
                    pass
            await db.delete(job)
            deleted_db += 1
        await db.commit()

    return {"deleted_db": deleted_db, "deleted_s3": deleted_s3, "cutoff": now.isoformat()}
