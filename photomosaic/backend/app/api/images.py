"""
이미지 관련 API 라우터

엔드포인트:
- POST /images/upload            개별 파일 업로드 (multipart)
- POST /images/upload/zip        ZIP 파일 업로드 및 압축 해제
- GET  /images                   이미지 목록 조회 (페이지네이션)
- GET  /images/{image_id}/thumbnail  썸네일 이미지 반환
- PATCH /images/{image_id}/target   타겟 이미지 설정
"""
import math
import os
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.dependencies import get_pagination, get_session_id
from app.models.schemas import (
    CommonResponse,
    ImageInfo,
    ImageListResponse,
    UploadResponse,
)
from app.services.image_service import (
    ALLOWED_EXTENSIONS,
    get_thumbnail_path,
    process_zip_file,
    save_image_file,
)
from app.services.session_service import session_service

router = APIRouter(prefix="/images", tags=["이미지"])
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/upload",
    response_model=CommonResponse[UploadResponse],
    status_code=200,
    summary="개별 이미지 파일 업로드",
)
@limiter.limit("30/minute")
async def upload_images(
    request: Request,
    files: List[UploadFile] = File(..., description="업로드할 이미지 파일 목록"),
    session_id: str = Depends(get_session_id),
):
    """
    multipart/form-data로 하나 이상의 이미지 파일을 업로드한다.
    허용 포맷: JPEG, PNG, WEBP
    파일당 최대 크기: 20MB
    세션당 최대 이미지 수: 1000개
    분당 최대 30회 호출 가능 (Rate Limit)
    """
    session = session_service.create_if_not_exists(session_id)
    uploaded: List[ImageInfo] = []
    failed: List[dict] = []

    for upload_file in files:
        # 세션 최대 이미지 수 초과 확인
        if len(session.images) >= settings.MAX_IMAGES_PER_SESSION:
            failed.append({
                "filename": upload_file.filename or "unknown",
                "error": f"세션 최대 이미지 수({settings.MAX_IMAGES_PER_SESSION}개) 초과",
            })
            continue

        filename = upload_file.filename or "unknown"

        try:
            # 파일 데이터 읽기
            file_data = await upload_file.read()

            # 세션 총 용량 확인
            if session.total_size_bytes() + len(file_data) > settings.MAX_TOTAL_SIZE_BYTES:
                failed.append({
                    "filename": filename,
                    "error": f"세션 최대 저장 용량({settings.MAX_TOTAL_SIZE_MB}MB) 초과",
                })
                continue

            # 이미지 저장 처리
            image_info = save_image_file(file_data, filename, session)
            if image_info:
                uploaded.append(image_info)

        except ValueError as e:
            failed.append({"filename": filename, "error": str(e)})
        except Exception as e:
            failed.append({"filename": filename, "error": f"서버 내부 오류: {str(e)}"})
        finally:
            await upload_file.close()

    response_data = UploadResponse(
        uploaded=uploaded,
        failed=failed,
        total_count=len(session.images),
    )
    return CommonResponse.ok(response_data)


@router.post(
    "/upload/zip",
    response_model=CommonResponse[UploadResponse],
    status_code=200,
    summary="ZIP 파일 업로드 및 압축 해제",
)
@limiter.limit("30/minute")
async def upload_zip(
    request: Request,
    file: UploadFile = File(..., description="ZIP 파일"),
    session_id: str = Depends(get_session_id),
):
    """
    ZIP 파일을 업로드하면 내부 이미지를 자동으로 압축 해제하여 저장한다.
    ZIP Bomb 방지: 압축 해제 크기 3GB 초과 시 거부
    분당 최대 30회 호출 가능 (Rate Limit)
    """
    session = session_service.create_if_not_exists(session_id)

    filename = file.filename or "upload.zip"
    if not filename.lower().endswith(".zip"):
        return CommonResponse.fail(
            code="INVALID_FILE_TYPE",
            message="ZIP 파일만 업로드 가능합니다.",
        )

    try:
        zip_data = await file.read()

        # ZIP 파일 크기 확인
        zip_size_mb = len(zip_data) / (1024 * 1024)
        if zip_size_mb > settings.MAX_TOTAL_SIZE_MB:
            return CommonResponse.fail(
                code="FILE_TOO_LARGE",
                message=f"ZIP 파일 크기가 최대 허용 크기({settings.MAX_TOTAL_SIZE_MB}MB)를 초과합니다.",
            )

        uploaded, failed = process_zip_file(zip_data, session)

        response_data = UploadResponse(
            uploaded=uploaded,
            failed=failed,
            total_count=len(session.images),
        )
        return CommonResponse.ok(response_data)

    except ValueError as e:
        return CommonResponse.fail(code="ZIP_PROCESSING_ERROR", message=str(e))
    except Exception as e:
        return CommonResponse.fail(
            code="INTERNAL_ERROR",
            message=f"ZIP 처리 중 오류가 발생했습니다: {str(e)}",
        )
    finally:
        await file.close()


@router.get(
    "",
    response_model=CommonResponse[ImageListResponse],
    summary="이미지 목록 조회",
)
async def list_images(
    session_id: str = Depends(get_session_id),
    pagination: dict = Depends(get_pagination),
):
    """
    현재 세션의 이미지 목록을 페이지네이션으로 조회한다.
    """
    session = session_service.get_session(session_id)
    if session is None:
        # 세션이 없으면 빈 목록 반환
        response_data = ImageListResponse(
            items=[],
            total=0,
            page=1,
            page_size=pagination["page_size"],
            total_pages=0,
        )
        return CommonResponse.ok(response_data)

    page = pagination["page"]
    page_size = pagination["page_size"]

    # 이미지 목록 (등록 순서 유지)
    all_images = list(session.images.values())
    total = len(all_images)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # 페이지네이션 슬라이싱
    start = (page - 1) * page_size
    end = start + page_size
    items = all_images[start:end]

    response_data = ImageListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
    return CommonResponse.ok(response_data)


@router.get(
    "/{image_id}/thumbnail",
    summary="썸네일 이미지 반환",
    response_class=FileResponse,
)
async def get_thumbnail(
    image_id: str,
    session_id: str = Depends(get_session_id),
):
    """
    지정된 이미지의 썸네일을 바이너리로 반환한다.
    Content-Type: image/jpeg
    """
    # Path Traversal 방지: image_id 검증
    if "/" in image_id or "\\" in image_id or ".." in image_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_IMAGE_ID", "message": "유효하지 않은 이미지 ID입니다."},
        )

    session = session_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "세션을 찾을 수 없습니다."},
        )

    if image_id not in session.images:
        raise HTTPException(
            status_code=404,
            detail={"code": "IMAGE_NOT_FOUND", "message": "이미지를 찾을 수 없습니다."},
        )

    thumbnail_path = get_thumbnail_path(image_id, session)
    if thumbnail_path is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "THUMBNAIL_NOT_FOUND", "message": "썸네일 파일을 찾을 수 없습니다."},
        )

    return FileResponse(
        path=thumbnail_path,
        media_type="image/jpeg",
        filename=f"{image_id}_thumb.jpg",
    )


@router.patch(
    "/{image_id}/target",
    response_model=CommonResponse[ImageInfo],
    summary="타겟 이미지 설정",
)
async def set_target_image(
    image_id: str,
    session_id: str = Depends(get_session_id),
):
    """
    지정된 이미지를 모자이크 생성의 타겟 이미지로 설정한다.
    기존 타겟 이미지는 자동으로 해제된다.
    """
    # Path Traversal 방지
    if "/" in image_id or "\\" in image_id or ".." in image_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_IMAGE_ID", "message": "유효하지 않은 이미지 ID입니다."},
        )

    session = session_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SESSION_NOT_FOUND", "message": "세션을 찾을 수 없습니다."},
        )

    if image_id not in session.images:
        raise HTTPException(
            status_code=404,
            detail={"code": "IMAGE_NOT_FOUND", "message": "이미지를 찾을 수 없습니다."},
        )

    # 기존 타겟 이미지 해제
    if session.target_image_id and session.target_image_id in session.images:
        old_target = session.images[session.target_image_id]
        # ImageInfo는 불변이므로 새 객체 생성
        session.images[session.target_image_id] = old_target.model_copy(
            update={"is_target": False}
        )

    # 새 타겟 이미지 설정
    session.target_image_id = image_id
    target_info = session.images[image_id]
    updated_info = target_info.model_copy(update={"is_target": True})
    session.images[image_id] = updated_info
    session.touch()

    return CommonResponse.ok(updated_info)
