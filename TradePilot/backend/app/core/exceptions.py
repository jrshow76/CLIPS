"""도메인 예외 + 글로벌 예외 핸들러.

에러 코드 체계는 `docs/14_exception_policy.md` §2.1을 따른다.
- Exxxx 형태의 4자리 숫자 코드.
- HTTP 상태코드 매핑은 ERROR_CODE_HTTP 테이블에 정의.
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.core.response import error_response

log = get_logger(__name__)


# ----------------------------------------------------------------------------
# 에러 코드 → HTTP 매핑 (docs/14_exception_policy.md §2.1 + docs/24 §3 일치)
# ----------------------------------------------------------------------------
ERROR_CODE_HTTP: dict[str, int] = {
    # 공통/시스템
    "E0001": 401, "E0002": 403, "E0003": 400, "E0004": 502, "E0005": 500,
    "E0006": 409, "E0007": 409, "E0008": 429, "E0009": 503,
    # 인증/모드 전환
    "E0011": 401, "E0012": 502, "E0013": 403, "E0014": 502, "E0015": 502,
    "E0016": 403, "E0017": 409,
    # 주문/매매
    "E0021": 422, "E0022": 409, "E0023": 502, "E0024": 422, "E0025": 502,
    "E0026": 422, "E0027": 422, "E0028": 409,
    # 백테스트
    "E0031": 410, "E0032": 422, "E0033": 500,
    # ML
    "E0041": 404, "E0042": 500,
    # 사용자/계정
    "E0051": 409, "E0052": 423, "E0053": 410, "E0054": 400, "E0055": 422,
    # 시세/시장
    "E0061": 502, "E0062": 404, "E0063": 422,
    # 외부 시스템
    "E0071": 502, "E0072": 504,
    # 알림
    "E0081": 502, "E0082": 422,
    # 운영
    "E0091": 503, "E0092": 403,
}


# ----------------------------------------------------------------------------
# 사용자 메시지 기본값 (도메인별 서비스에서 override 가능)
# ----------------------------------------------------------------------------
DEFAULT_MESSAGES: dict[str, str] = {
    "E0001": "인증이 필요합니다.",
    "E0002": "권한이 없습니다.",
    "E0003": "입력값을 확인해주세요.",
    "E0004": "외부 시스템 응답이 지연되거나 오류가 발생했습니다.",
    "E0005": "일시적인 오류가 발생했습니다.",
    "E0006": "매매 모드가 일치하지 않습니다.",
    "E0007": "장 운영시간이 아닙니다.",
    "E0008": "요청이 너무 많습니다.",
    "E0009": "서비스 점검 중입니다.",
    "E0011": "인증번호가 올바르지 않습니다.",
    "E0012": "크레온 연결에 실패했습니다.",
    "E0013": "약관 동의가 필요합니다.",
    "E0014": "미체결 주문 취소에 실패했습니다.",
    "E0015": "비상정지 처리 중 일부 실패가 발생했습니다.",
    "E0016": "실거래 전환 사전 조건이 충족되지 않았습니다.",
    "E0017": "이미 모드 전환이 진행 중입니다.",
    "E0021": "한도를 초과했습니다.",
    "E0022": "동일 주문이 처리 중입니다.",
    "E0023": "증권사 주문 처리 오류가 발생했습니다.",
    "E0024": "증거금이 부족합니다.",
    "E0025": "강제 청산 일부 실패가 발생했습니다.",
    "E0026": "호가 단위 또는 매매 단위 오류입니다.",
    "E0027": "상한가/하한가 도달로 주문할 수 없습니다.",
    "E0028": "종목 거래가 정지되었습니다.",
    "E0031": "백테스트 결과가 만료되었습니다.",
    "E0032": "백테스트 입력값 범위를 초과했습니다.",
    "E0033": "백테스트 워커 오류가 발생했습니다.",
    "E0041": "학습되지 않은 종목입니다.",
    "E0042": "학습에 실패했습니다.",
    "E0051": "이미 가입된 이메일입니다.",
    "E0052": "계정이 잠겨있습니다.",
    "E0053": "토큰이 만료되었습니다.",
    "E0054": "비밀번호 재설정 토큰 오류입니다.",
    "E0055": "비밀번호 정책에 위반됩니다.",
    "E0061": "시세 데이터가 일시적으로 지연되고 있습니다.",
    "E0062": "종목을 찾을 수 없습니다.",
    "E0063": "요청 기간이 너무 깁니다.",
    "E0071": "외부 데이터 소스 오류입니다.",
    "E0072": "외부 시스템 타임아웃이 발생했습니다.",
    "E0081": "알림 발송에 실패했습니다.",
    "E0082": "알림 채널이 설정되지 않았습니다.",
    "E0091": "시스템 점검 중입니다.",
    "E0092": "관리자 권한이 필요합니다.",
}


# ----------------------------------------------------------------------------
# 도메인 예외 베이스
# ----------------------------------------------------------------------------
class AppException(Exception):
    """도메인 예외 베이스 클래스.

    예시:
        raise AppException("E0021", details={"limit": 5_000_000, "attempted": 5_500_000})
    """

    def __init__(
        self,
        code: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        http_status: int | None = None,
    ) -> None:
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "오류가 발생했습니다.")
        self.details = details or {}
        self.http_status = http_status or ERROR_CODE_HTTP.get(code, 500)
        super().__init__(f"[{code}] {self.message}")


# ----------------------------------------------------------------------------
# 글로벌 예외 핸들러 등록
# ----------------------------------------------------------------------------
def register_exception_handlers(app: Any) -> None:
    """FastAPI 앱에 글로벌 예외 핸들러를 등록한다."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        log.warning(
            "app_exception",
            code=exc.code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
        )
        return error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            http_status=exc.http_status,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic 검증 실패 → E0003
        field_errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query"))
            field_errors.setdefault(loc or "_", []).append(err.get("msg", "invalid"))
        log.info("validation_error", path=request.url.path, errors=field_errors)
        return error_response(
            code="E0003",
            message=DEFAULT_MESSAGES["E0003"],
            details=jsonable_encoder(field_errors),
            http_status=400,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # FastAPI 내부 HTTPException → 적절한 E 코드로 매핑
        if exc.status_code == 401:
            code = "E0001"
        elif exc.status_code == 403:
            code = "E0002"
        elif exc.status_code == 404:
            code = "E0062"
        elif exc.status_code == 429:
            code = "E0008"
        else:
            code = "E0005"
        log.info("http_exception", path=request.url.path, status=exc.status_code, detail=exc.detail)
        return error_response(
            code=code,
            message=str(exc.detail) if exc.detail else DEFAULT_MESSAGES.get(code, ""),
            http_status=exc.status_code,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        log.error("db_integrity_error", path=request.url.path, error=str(exc.orig))
        return error_response(
            code="E0022",
            message="중복 또는 제약 조건 위반입니다.",
            details={"db_error": str(exc.orig)[:200]},
            http_status=409,
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.exception("db_error", path=request.url.path)
        return error_response(
            code="E0005",
            message="데이터베이스 오류가 발생했습니다.",
            http_status=500,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", path=request.url.path)
        return error_response(
            code="E0005",
            message=DEFAULT_MESSAGES["E0005"],
            http_status=500,
        )
