"""
세션 관리 API 라우터

엔드포인트:
- DELETE /sessions/{session_id}   세션 초기화 (모든 이미지 및 데이터 삭제)
"""
from fastapi import APIRouter, HTTPException

from app.models.schemas import CommonResponse
from app.services.session_service import session_service

router = APIRouter(prefix="/sessions", tags=["세션"])


@router.delete(
    "/{session_id}",
    response_model=CommonResponse[dict],
    summary="세션 초기화",
)
async def delete_session(session_id: str):
    """
    지정된 세션과 관련된 모든 데이터를 삭제한다.
    - 업로드된 이미지 파일
    - 썸네일 파일
    - 결과 파일
    - 세션 메타데이터

    Path Traversal 방지: session_id에 경로 구분자 포함 여부 검증
    """
    # Path Traversal 방지
    if "/" in session_id or "\\" in session_id or ".." in session_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SESSION_ID",
                "message": "세션 ID에 유효하지 않은 문자가 포함되어 있습니다.",
            },
        )

    deleted = session_service.delete_session(session_id)
    if not deleted:
        # 세션이 없어도 성공으로 처리 (멱등성 보장)
        return CommonResponse.ok({
            "session_id": session_id,
            "message": "세션이 존재하지 않거나 이미 삭제되었습니다.",
        })

    return CommonResponse.ok({
        "session_id": session_id,
        "message": "세션이 성공적으로 삭제되었습니다.",
    })
