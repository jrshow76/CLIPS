"""
모자이크 생성 관련 API 라우터

엔드포인트:
- POST   /mosaic/generate              모자이크 생성 시작 (비동기, 202 반환)
- GET    /mosaic/jobs/{job_id}/status  작업 진행 상태 조회 (polling)
- DELETE /mosaic/jobs/{job_id}         작업 취소
- GET    /mosaic/jobs/{job_id}/result  결과 파일 다운로드
"""
import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_session_id
from app.models.schemas import CommonResponse, GenerateRequest, JobStatus
from app.services import mosaic_service
from app.services.session_service import session_service

router = APIRouter(prefix="/mosaic", tags=["모자이크"])
limiter = Limiter(key_func=get_remote_address)

# 출력 포맷별 Content-Type 매핑
FORMAT_CONTENT_TYPE = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


@router.post(
    "/generate",
    response_model=CommonResponse[JobStatus],
    status_code=202,
    summary="모자이크 생성 시작",
)
@limiter.limit("10/minute")
async def generate_mosaic(
    request: Request,
    body: GenerateRequest,
):
    """
    포토모자이크 생성 작업을 비동기로 시작한다.

    - 즉시 202 Accepted를 반환하고 작업을 백그라운드에서 실행한다.
    - 반환된 job_id로 /mosaic/jobs/{job_id}/status를 polling하여 진행 상태를 확인한다.
    - 세션당 1개 작업만 동시 실행 가능하다.
    - 전체 최대 동시 작업 수는 MAX_CONCURRENT_JOBS로 제한된다.
    - 분당 최대 10회 호출 가능 (Rate Limit)
    """
    session_id = body.session_id

    # 세션 존재 확인
    session = session_service.get_session(session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content=CommonResponse.fail(
                code="SESSION_NOT_FOUND",
                message="세션을 찾을 수 없습니다. 이미지를 먼저 업로드하세요.",
            ).model_dump(),
        )

    # 타겟 이미지 존재 확인
    target_image_id = body.target_image_id
    if target_image_id not in session.images:
        return JSONResponse(
            status_code=404,
            content=CommonResponse.fail(
                code="TARGET_IMAGE_NOT_FOUND",
                message=f"타겟 이미지를 찾을 수 없습니다: {target_image_id}",
            ).model_dump(),
        )

    # 타일 이미지 존재 확인 (타겟 제외)
    tile_count = sum(
        1 for img_id in session.images if img_id != target_image_id
    )
    if tile_count == 0:
        return JSONResponse(
            status_code=400,
            content=CommonResponse.fail(
                code="NO_TILE_IMAGES",
                message="타일로 사용할 이미지가 없습니다. 타겟 이미지 외에 최소 1개 이상의 이미지가 필요합니다.",
            ).model_dump(),
        )

    try:
        job_id = await mosaic_service.generate_mosaic(
            session_id=session_id,
            target_image_id=target_image_id,
            options=body.options,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=409,
            content=CommonResponse.fail(code="JOB_CREATION_FAILED", message=str(e)).model_dump(),
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=CommonResponse.fail(
                code="INTERNAL_ERROR",
                message=f"작업 생성 중 오류가 발생했습니다: {str(e)}",
            ).model_dump(),
        )

    # 초기 작업 상태 반환
    job_status = JobStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        step="PENDING",
        step_message="작업 대기 중...",
        elapsed_seconds=0.0,
        result_url=None,
    )

    return CommonResponse.ok(job_status)


@router.get(
    "/jobs/{job_id}/status",
    response_model=CommonResponse[JobStatus],
    summary="작업 진행 상태 조회",
)
async def get_job_status(
    job_id: str,
    session_id: str = Depends(get_session_id),
):
    """
    작업 ID로 현재 진행 상태를 조회한다.
    프론트엔드에서 주기적으로 polling하여 완료 여부를 확인한다.

    상태값:
    - pending: 대기 중
    - running: 실행 중
    - completed: 완료
    - failed: 실패
    - cancelled: 취소됨
    """
    # Path Traversal 방지
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_JOB_ID", "message": "유효하지 않은 작업 ID입니다."},
        )

    job = mosaic_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "작업을 찾을 수 없습니다."},
        )

    # 세션 소유권 확인
    if job.get("session_id") != session_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "ACCESS_DENIED", "message": "해당 작업에 접근할 권한이 없습니다."},
        )

    elapsed = round(time.time() - job["start_time"], 2)

    # fallback 경고 메시지 구성
    warning = None
    if job.get("allow_tile_repeat_fallback"):
        warning = (
            "타일 이미지 수가 격자 수보다 적어 타일 반복(allow_tile_repeat=True) 모드로 자동 전환되었습니다."
        )

    job_status = JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        step=job["step"],
        step_message=job["step_message"],
        elapsed_seconds=elapsed,
        result_url=job.get("result_url"),
        warning=warning,
    )

    return CommonResponse.ok(job_status)


@router.delete(
    "/jobs/{job_id}",
    response_model=CommonResponse[dict],
    summary="작업 취소",
)
async def cancel_job(
    job_id: str,
    session_id: str = Depends(get_session_id),
):
    """
    진행 중인 작업을 취소한다.
    이미 완료/실패/취소된 작업에는 적용되지 않는다.
    """
    # Path Traversal 방지
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_JOB_ID", "message": "유효하지 않은 작업 ID입니다."},
        )

    job = mosaic_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "작업을 찾을 수 없습니다."},
        )

    # 세션 소유권 확인
    if job.get("session_id") != session_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "ACCESS_DENIED", "message": "해당 작업에 접근할 권한이 없습니다."},
        )

    cancelled = mosaic_service.cancel_job(job_id)
    if not cancelled:
        return JSONResponse(
            status_code=409,
            content=CommonResponse.fail(
                code="CANCEL_FAILED",
                message="작업을 취소할 수 없습니다. 이미 완료되었거나 실패한 작업입니다.",
            ).model_dump(),
        )

    return CommonResponse.ok({"job_id": job_id, "message": "작업이 취소되었습니다."})


@router.get(
    "/jobs/{job_id}/result",
    summary="결과 파일 다운로드",
    response_class=FileResponse,
)
async def download_result(
    job_id: str,
    session_id: str = Depends(get_session_id),
):
    """
    완료된 작업의 결과 이미지를 다운로드한다.
    작업이 완료되지 않았거나 결과 파일이 없으면 404를 반환한다.
    """
    # Path Traversal 방지
    if "/" in job_id or "\\" in job_id or ".." in job_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_JOB_ID", "message": "유효하지 않은 작업 ID입니다."},
        )

    job = mosaic_service.get_job_status(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "작업을 찾을 수 없습니다."},
        )

    # 세션 소유권 확인
    if job.get("session_id") != session_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "ACCESS_DENIED", "message": "해당 작업에 접근할 권한이 없습니다."},
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "JOB_NOT_COMPLETED",
                "message": f"작업이 아직 완료되지 않았습니다. 현재 상태: {job['status']}",
            },
        )

    result_path = mosaic_service.get_result_path(job_id)
    if result_path is None or not os.path.exists(result_path):
        raise HTTPException(
            status_code=404,
            detail={"code": "RESULT_NOT_FOUND", "message": "결과 파일을 찾을 수 없습니다."},
        )

    # 파일 확장자로 Content-Type 결정
    _, ext = os.path.splitext(result_path)
    ext = ext.lstrip(".").lower()
    content_type = FORMAT_CONTENT_TYPE.get(ext, "application/octet-stream")
    download_filename = f"mosaic_{job_id}.{ext}"

    return FileResponse(
        path=result_path,
        media_type=content_type,
        filename=download_filename,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )
