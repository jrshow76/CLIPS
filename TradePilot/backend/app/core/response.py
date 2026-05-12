"""공통 응답 포맷 헬퍼.

`docs/24_api_response_spec.md` §2 규약을 따른다.

성공:
    { "success": true, "data": <object|array> }
페이지:
    { "success": true, "data": { items, page, size, total, has_next } }
실패:
    { "success": false, "error": { code, message, details, trace_id, ts } }
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

_KST = ZoneInfo("Asia/Seoul")


def _now_iso() -> str:
    return datetime.now(tz=_KST).isoformat(timespec="seconds")


def _current_trace_id() -> str | None:
    """structlog 컨텍스트에서 trace_id 추출. 없으면 None."""
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("trace_id") if isinstance(ctx, dict) else None


def success_response(
    data: Any = None,
    http_status: int = 200,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """단일/페이지/액션 공통 성공 응답."""
    body = {"success": True, "data": jsonable_encoder(data)}
    return JSONResponse(content=body, status_code=http_status, headers=headers)


def page_response(
    items: list[Any],
    page: int,
    size: int,
    total: int | None,
    has_next: bool,
    http_status: int = 200,
) -> JSONResponse:
    """페이지 응답."""
    return success_response(
        data={
            "items": jsonable_encoder(items),
            "page": page,
            "size": size,
            "total": total,
            "has_next": has_next,
        },
        http_status=http_status,
    )


def accepted_response(
    job_id: str | None = None,
    status: str = "QUEUED",
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """비동기 작업 수락 응답 (HTTP 202)."""
    data: dict[str, Any] = {"status": status}
    if job_id:
        data["job_id"] = job_id
    if extra:
        data.update(extra)
    return success_response(data=data, http_status=202)


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    http_status: int = 500,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """표준 오류 응답."""
    body = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": jsonable_encoder(details) if details else {},
            "trace_id": _current_trace_id(),
            "ts": _now_iso(),
        },
    }
    return JSONResponse(content=body, status_code=http_status, headers=headers)
