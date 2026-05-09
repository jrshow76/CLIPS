"""
FastAPI 의존성 주입 모듈
공통 의존성 함수를 정의한다.
"""
from fastapi import Header, HTTPException, Query
from typing import Optional


async def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    session_id: Optional[str] = Query(None, description="세션 ID (헤더 대신 쿼리 파라미터로 전달 가능)"),
) -> str:
    """
    요청 헤더 또는 쿼리 파라미터에서 세션 ID를 추출한다.
    헤더 우선, 없으면 쿼리 파라미터를 사용한다.
    img src 같이 헤더를 전송할 수 없는 경우 ?session_id=... 방식을 사용한다.
    """
    actual_id = x_session_id or session_id
    if not actual_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_SESSION_ID",
                "message": "X-Session-ID 헤더 또는 session_id 쿼리 파라미터가 필요합니다.",
            },
        )
    # Path Traversal 방지: 세션 ID에 경로 구분자 포함 여부 확인
    if "/" in actual_id or "\\" in actual_id or ".." in actual_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SESSION_ID",
                "message": "세션 ID에 유효하지 않은 문자가 포함되어 있습니다.",
            },
        )
    return actual_id


def get_pagination(
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
):
    """페이지네이션 파라미터를 반환한다."""
    return {"page": page, "page_size": page_size}
