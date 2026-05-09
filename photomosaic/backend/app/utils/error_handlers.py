"""
전역 에러 핸들러 유틸리티
FastAPI 애플리케이션에 공통 에러 응답 형식을 적용한다.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


def register_error_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 전역 에러 핸들러를 등록한다."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP 예외를 공통 응답 형식으로 변환한다."""
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code", "HTTP_ERROR")
            message = detail.get("message", str(exc.detail))
        else:
            code = f"HTTP_{exc.status_code}"
            message = str(detail)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "error": {"code": code, "message": message},
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """요청 데이터 검증 오류를 공통 응답 형식으로 변환한다."""
        # 첫 번째 에러 메시지를 대표 메시지로 사용
        errors = exc.errors()
        if errors:
            first_error = errors[0]
            field = " -> ".join(str(loc) for loc in first_error.get("loc", []))
            message = f"입력값 오류 [{field}]: {first_error.get('msg', '알 수 없는 오류')}"
        else:
            message = "요청 데이터 형식이 올바르지 않습니다."

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "data": None,
                "error": {"code": "VALIDATION_ERROR", "message": message},
            },
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        """Rate Limit 초과 시 공통 응답 형식으로 변환한다."""
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "요청 횟수가 제한을 초과했습니다. 잠시 후 다시 시도하세요.",
                },
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """예상치 못한 서버 오류를 공통 응답 형식으로 변환한다."""
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "서버 내부 오류가 발생했습니다.",
                },
            },
        )
