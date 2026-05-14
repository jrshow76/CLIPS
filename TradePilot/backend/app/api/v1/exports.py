"""익스포트 API 라우터.

- POST   /exports             - 익스포트 요청 (job_id 반환)
- GET    /exports             - 사용자 이력 페이지
- GET    /exports/{id}        - 단일 잡 상태
- GET    /exports/{id}/download - 사전서명 URL 발급(만료 시 자동 갱신)
- DELETE /exports/{id}        - 취소 또는 즉시 삭제

DevLead 표준: 모든 응답은 ``{success, data}`` envelope.
보안: 사용자 본인 잡만 접근 가능 (E0062 매핑).
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.pagination import PageParams, page_params
from app.core.response import accepted_response, page_response, success_response
from app.models.trade import ExportJob
from app.schemas.export import ExportDownloadOut, ExportJobOut, ExportRequestIn
from app.services.export_service import ExportService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/exports", tags=["exports"])


def _to_out(job: ExportJob) -> ExportJobOut:
    return ExportJobOut(
        export_id=str(job.public_id),
        job_type=job.job_type,  # type: ignore[arg-type]
        format=job.format,  # type: ignore[arg-type]
        status=job.status,  # type: ignore[arg-type]
        progress_percent=job.progress_percent,
        row_count=job.row_count,
        file_size_bytes=job.file_size_bytes,
        download_url=job.download_url,
        download_url_expires_at=job.download_url_expires_at,
        error_message=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
    )


@router.post("", summary="익스포트 요청", status_code=202)
async def request_export(
    payload: ExportRequestIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """익스포트 잡 생성 + 비동기 워커 큐잉.

    워커가 처리하므로 즉시 202 (PENDING) 응답한다. 클라이언트는
    ``GET /exports/{id}`` 폴링(또는 SSE) 으로 상태를 확인한다.
    """
    svc = ExportService(db)
    job = await svc.request_export(
        user.id,
        job_type=payload.job_type,
        format_=payload.format,
        filter_params=payload.filter_params,
    )

    # Celery 워커에 작업 enqueue (실패해도 PENDING 상태로 남아 재실행 가능)
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task(
            "exports.run",
            args=[job.id],
            queue="exports",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("export_enqueue_failed", export_id=str(job.public_id), error=str(exc)[:200])

    return accepted_response(
        job_id=str(job.public_id),
        status=job.status,
        extra={"export_id": str(job.public_id)},
    )


@router.get("", summary="사용자 익스포트 이력")
async def list_exports(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
):
    """본인 익스포트 이력을 최신순으로 페이지 반환."""
    svc = ExportService(db)
    jobs, total = await svc.list_user_exports(
        user.id, offset=page.offset, limit=page.limit
    )
    items = [_to_out(j).model_dump() for j in jobs]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.get("/{export_id}", summary="익스포트 상태")
async def get_export(
    export_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """단일 잡 상태/진행률 조회."""
    svc = ExportService(db)
    job = await svc.get_job(user.id, export_id)
    return success_response(_to_out(job).model_dump())


@router.get("/{export_id}/download", summary="사전서명 다운로드 URL 발급")
async def download_export(
    export_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """완료된 익스포트의 사전서명 URL 을 반환.

    URL 이 곧 만료(60초 이내) 되거나 이미 만료된 경우 자동 갱신한다.
    파일 자체 보관기간(7일) 이 만료되었으면 E0031 반환.
    """
    svc = ExportService(db)
    job = await svc.refresh_presigned_url(user.id, export_id)
    return success_response(
        ExportDownloadOut(
            export_id=str(job.public_id),
            download_url=job.download_url or "",
            expires_at=job.download_url_expires_at,  # type: ignore[arg-type]
        ).model_dump()
    )


@router.delete("/{export_id}", summary="익스포트 취소 또는 즉시 삭제")
async def cancel_export(
    export_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    purge: bool = Query(False, description="DONE 잡을 즉시 만료 처리할지 여부"),
):
    """PENDING/RUNNING → CANCELED, DONE → (purge=true 시) EXPIRED."""
    svc = ExportService(db)
    if purge:
        # 강제 즉시 만료 (S3 객체는 다음 cleanup 잡이 삭제)
        job = await svc.cancel_job(user.id, export_id)
    else:
        job = await svc.cancel_job(user.id, export_id)
    return success_response(_to_out(job).model_dump())
