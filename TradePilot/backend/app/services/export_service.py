"""익스포트 서비스 레이어.

API 라우터와 Celery 워커가 공유한다.
한도:
    * 사용자당 동시 PENDING/RUNNING 잡 최대 3건 (E0021)
    * 사용자당 일일 신규 요청 최대 20건 (E0021)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.trade import ExportJob
from app.services.export_engine.config import ExportConfig, get_export_config

log = structlog.get_logger(__name__)

# 허용 입력값
ALLOWED_JOB_TYPES = ("ORDERS", "PNL", "BACKTEST", "SIGNALS", "POSITIONS")
ALLOWED_FORMATS = ("CSV", "XLSX")


class ExportService:
    """익스포트 잡 라이프사이클 관리."""

    def __init__(self, db: AsyncSession, config: ExportConfig | None = None) -> None:
        self.db = db
        self.config = config or get_export_config()

    # ------------------------------------------------------------------
    # 요청
    # ------------------------------------------------------------------
    async def request_export(
        self,
        user_id: int,
        *,
        job_type: str,
        format_: str = "CSV",
        filter_params: Mapping[str, Any] | None = None,
    ) -> ExportJob:
        """신규 익스포트 잡 생성. 한도 초과 시 E0021.

        Returns:
            ``status='PENDING'`` 잡 ORM 객체 (commit 완료, refresh 됨).
        """
        jt = job_type.upper()
        fmt = format_.upper()
        if jt not in ALLOWED_JOB_TYPES:
            raise AppException(
                "E0003",
                message=f"지원하지 않는 익스포트 종류입니다: {job_type}",
                details={"job_type": list(ALLOWED_JOB_TYPES)},
            )
        if fmt not in ALLOWED_FORMATS:
            raise AppException(
                "E0003",
                message=f"지원하지 않는 포맷입니다: {format_}",
                details={"format": list(ALLOWED_FORMATS)},
            )

        # 한도 검사
        await self._enforce_limits(user_id)

        job = ExportJob(
            user_id=user_id,
            job_type=jt,
            format=fmt,
            filter_params=dict(filter_params or {}),
            status="PENDING",
            progress_percent=0,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        log.info(
            "export_requested",
            user_id=user_id,
            export_id=str(job.public_id),
            job_type=jt,
            format=fmt,
        )
        return job

    async def _enforce_limits(self, user_id: int) -> None:
        """동시/일일 한도 검사."""
        # 1) 동시 PENDING/RUNNING
        active_stmt = (
            select(func.count())
            .select_from(ExportJob)
            .where(
                and_(
                    ExportJob.user_id == user_id,
                    ExportJob.status.in_(["PENDING", "RUNNING"]),
                )
            )
        )
        active = int((await self.db.execute(active_stmt)).scalar() or 0)
        if active >= self.config.concurrent_per_user:
            raise AppException(
                "E0021",
                message=(
                    f"동시에 진행 가능한 익스포트는 최대 {self.config.concurrent_per_user}건 입니다."
                ),
                details={"active": active, "limit": self.config.concurrent_per_user},
            )

        # 2) 일일 누적
        today_start = datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        daily_stmt = (
            select(func.count())
            .select_from(ExportJob)
            .where(
                and_(
                    ExportJob.user_id == user_id,
                    ExportJob.created_at >= today_start,
                )
            )
        )
        daily = int((await self.db.execute(daily_stmt)).scalar() or 0)
        if daily >= self.config.daily_limit_per_user:
            raise AppException(
                "E0021",
                message=(
                    f"오늘 가능한 익스포트 요청 한도({self.config.daily_limit_per_user}건)를 초과했습니다."
                ),
                details={"today": daily, "limit": self.config.daily_limit_per_user},
            )

    # ------------------------------------------------------------------
    # 조회
    # ------------------------------------------------------------------
    async def get_job(self, user_id: int, export_id: str) -> ExportJob:
        """사용자 본인 잡 1건 조회. 없으면 E0062."""
        import uuid as _uuid

        try:
            uid = _uuid.UUID(export_id)
        except (TypeError, ValueError) as exc:
            raise AppException(
                "E0062", message="익스포트 ID 형식이 올바르지 않습니다."
            ) from exc

        stmt = select(ExportJob).where(
            and_(ExportJob.public_id == uid, ExportJob.user_id == user_id)
        )
        job = (await self.db.execute(stmt)).scalar_one_or_none()
        if job is None:
            raise AppException("E0062", message="익스포트 잡을 찾을 수 없습니다.")
        return job

    async def list_user_exports(
        self,
        user_id: int,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ExportJob], int]:
        """사용자 익스포트 이력 페이지."""
        count_stmt = (
            select(func.count())
            .select_from(ExportJob)
            .where(ExportJob.user_id == user_id)
        )
        total = int((await self.db.execute(count_stmt)).scalar() or 0)

        stmt = (
            select(ExportJob)
            .where(ExportJob.user_id == user_id)
            .order_by(ExportJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, total

    # ------------------------------------------------------------------
    # 취소 / 삭제
    # ------------------------------------------------------------------
    async def cancel_job(self, user_id: int, export_id: str) -> ExportJob:
        """PENDING/RUNNING 잡 취소. DONE 은 EXPIRED 마킹으로 즉시 삭제 처리.

        DONE 잡 취소 시 S3 객체는 cleanup_expired 잡이 비동기 삭제한다.
        """
        job = await self.get_job(user_id, export_id)
        if job.status in ("PENDING", "RUNNING"):
            job.status = "CANCELED"
            job.completed_at = datetime.now(tz=timezone.utc)
            await self.db.commit()
        elif job.status == "DONE":
            # 즉시 만료 처리 (cleanup beat 가 다음 실행에서 S3 객체 + 행 삭제)
            job.expires_at = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
            job.status = "EXPIRED"
            await self.db.commit()
        return job

    # ------------------------------------------------------------------
    # 사전서명 URL 갱신
    # ------------------------------------------------------------------
    async def refresh_presigned_url(
        self,
        user_id: int,
        export_id: str,
        *,
        uploader=None,
    ) -> ExportJob:
        """다운로드 URL 만료 시 새 사전서명 URL 발급."""
        job = await self.get_job(user_id, export_id)
        if job.status != "DONE" or not job.file_path:
            raise AppException(
                "E0062",
                message="아직 완료되지 않은 익스포트입니다.",
                details={"status": job.status},
            )
        # 만료된 잡(파일이 cleanup 으로 삭제된 경우)
        if job.expires_at and job.expires_at < datetime.now(tz=timezone.utc):
            raise AppException("E0031", message="익스포트 보관 기간이 만료되었습니다.")

        # 이미 유효한 URL 이면 재사용
        now = datetime.now(tz=timezone.utc)
        if (
            job.download_url
            and job.download_url_expires_at
            and job.download_url_expires_at > now + timedelta(seconds=60)
        ):
            return job

        # 새 URL 발급
        from app.services.export_engine.s3_uploader import S3Uploader

        up = uploader or S3Uploader(self.config)
        new_url = up.generate_presigned_url(
            job.file_path, ttl_sec=self.config.presign_ttl_sec
        )
        job.download_url = new_url
        job.download_url_expires_at = now + timedelta(seconds=self.config.presign_ttl_sec)
        await self.db.commit()
        return job
