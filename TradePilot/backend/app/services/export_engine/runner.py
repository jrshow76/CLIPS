"""익스포트 러너 - 진입점.

흐름:
    1. job 조회 + RUNNING 마킹 (진행률 0% → 10%)
    2. extractor 실행 (10% → 60%)
    3. 포맷 직렬화 (60% → 90%)
    4. S3 업로드 + 사전서명 URL (90% → 100%)
    5. DB 갱신 (DONE / 오류 시 FAILED)

진행률은 Redis pub/sub 채널 ``export:{public_id}`` 로 publish 하여 클라이언트
실시간 표시를 지원한다(미구현 환경에서도 동작에 영향 없음).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.export_engine.config import ExportConfig, get_export_config
from app.services.export_engine.extractors import EXTRACTORS
from app.services.export_engine.formats import write_csv, write_xlsx
from app.services.export_engine.s3_uploader import (
    S3Uploader,
    content_type_for,
    extension_for,
)

log = structlog.get_logger(__name__)


@dataclass
class ExportResult:
    """러너 반환값."""

    status: str  # DONE / FAILED / EMPTY
    file_path: str | None
    file_size_bytes: int
    row_count: int
    download_url: str | None
    download_url_expires_at: datetime | None
    error_message: str | None = None


async def run_export(
    db: AsyncSession,
    job_id: int,
    *,
    uploader: S3Uploader | None = None,
    config: ExportConfig | None = None,
    progress_cb: Any | None = None,
) -> ExportResult:
    """단일 export_job 을 실행한다.

    Args:
        db: 비동기 SQLAlchemy 세션. 호출 측이 트랜잭션 책임.
        job_id: ``export_jobs.id``.
        uploader: 테스트에서 stub 주입. None 이면 기본 S3Uploader 생성.
        config: 테스트 오버라이드. None 이면 환경변수에서 로드.
        progress_cb: 진행률 콜백. ``cb(pct: int, stage: str)``.

    Returns:
        ExportResult. 호출 측은 본 결과로 export_jobs 행을 갱신해야 한다.
    """
    from app.models.trade import ExportJob

    cfg = config or get_export_config()
    up = uploader or S3Uploader(cfg)
    cb = progress_cb or (lambda pct, stage: None)

    job = (
        await db.execute(select(ExportJob).where(ExportJob.id == job_id))
    ).scalar_one_or_none()
    if job is None:
        return ExportResult(
            status="FAILED",
            file_path=None,
            file_size_bytes=0,
            row_count=0,
            download_url=None,
            download_url_expires_at=None,
            error_message=f"export_job not found: {job_id}",
        )

    if job.status in ("DONE", "CANCELED", "EXPIRED"):
        # 이미 처리됨
        return ExportResult(
            status=job.status,
            file_path=job.file_path,
            file_size_bytes=job.file_size_bytes or 0,
            row_count=job.row_count or 0,
            download_url=job.download_url,
            download_url_expires_at=job.download_url_expires_at,
        )

    # 1. RUNNING 마킹
    job.status = "RUNNING"
    job.started_at = datetime.now(tz=timezone.utc)
    job.progress_percent = 5
    await db.commit()
    cb(5, "START")

    try:
        # 2. 추출
        extractor = EXTRACTORS.get(job.job_type)
        if extractor is None:
            raise ValueError(f"unsupported job_type: {job.job_type}")

        cb(10, "EXTRACT")
        sheets = await extractor(db, job.user_id, dict(job.filter_params or {}))
        row_count = sum(0 if df is None else len(df) for df in sheets.values())

        if row_count > cfg.max_rows:
            raise ValueError(
                f"row count {row_count} exceeds limit {cfg.max_rows}"
            )

        job.progress_percent = 50
        await db.commit()
        cb(60, "SERIALIZE")

        # 3. 직렬화
        ext = extension_for(job.format)
        ctype = content_type_for(job.format)
        if job.format.upper() == "XLSX":
            payload = write_xlsx(sheets)
        else:
            # CSV 는 첫 번째 시트(메인)만 사용한다 (다중 시트 합쳐 표현이 모호)
            main_df = next(iter(sheets.values())) if sheets else pd.DataFrame()
            payload = write_csv(main_df)

        job.progress_percent = 85
        await db.commit()
        cb(90, "UPLOAD")

        # 4. S3 업로드
        key = cfg.object_key(job.user_id, str(job.public_id), ext)
        up.upload_bytes(payload, key, content_type=ctype)

        # 5. 사전서명 URL
        url = up.generate_presigned_url(key, ttl_sec=cfg.presign_ttl_sec)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=cfg.presign_ttl_sec)
        retention_expiry = datetime.now(tz=timezone.utc) + timedelta(hours=cfg.retention_hours)

        # 6. DB 갱신
        job.status = "DONE"
        job.progress_percent = 100
        job.file_path = key
        job.file_size_bytes = len(payload)
        job.row_count = row_count
        job.download_url = url
        job.download_url_expires_at = expires_at
        job.completed_at = datetime.now(tz=timezone.utc)
        job.expires_at = retention_expiry
        await db.commit()
        cb(100, "DONE")

        # 진행률 publish (best-effort)
        await _publish_progress(str(job.public_id), 100, "DONE")

        return ExportResult(
            status="DONE",
            file_path=key,
            file_size_bytes=len(payload),
            row_count=row_count,
            download_url=url,
            download_url_expires_at=expires_at,
        )

    except Exception as exc:  # noqa: BLE001
        log.exception("export_run_failed", job_id=job_id, job_type=job.job_type)
        job.status = "FAILED"
        job.error_message = str(exc)[:1000]
        job.completed_at = datetime.now(tz=timezone.utc)
        await db.commit()
        await _publish_progress(str(job.public_id), job.progress_percent or 0, "FAILED")
        return ExportResult(
            status="FAILED",
            file_path=None,
            file_size_bytes=0,
            row_count=0,
            download_url=None,
            download_url_expires_at=None,
            error_message=str(exc)[:1000],
        )


async def _publish_progress(public_id: str, pct: int, stage: str) -> None:
    """Redis 채널에 진행률 publish. 실패해도 익스포트 자체에는 영향 없음."""
    try:
        from app.core.redis_client import get_redis

        await get_redis().publish(
            f"export:{public_id}",
            json.dumps({"progress": pct, "stage": stage}),
        )
    except Exception:  # noqa: BLE001 - best effort
        pass
