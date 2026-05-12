"""미들웨어: TraceId, 요청 로깅, 슬라이딩 윈도우 RateLimit.

CORS는 main.py에서 FastAPI CORSMiddleware로 별도 등록한다.
"""
from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import bind_trace, clear_trace, get_logger
from app.core.redis_client import get_redis
from app.core.response import error_response

log = get_logger(__name__)


class TraceIdMiddleware(BaseHTTPMiddleware):
    """X-Request-Id 헤더가 있으면 채택, 없으면 UUID 생성.

    structlog 컨텍스트에 trace_id를 바인딩하고, 응답 헤더에 X-Request-Id를 포함한다.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        trace_id = request.headers.get("X-Request-Id") or uuid4().hex
        request.state.trace_id = trace_id
        bind_trace(trace_id=trace_id, path=request.url.path, method=request.method)
        try:
            response = await call_next(request)
        finally:
            clear_trace()
        response.headers["X-Request-Id"] = trace_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """모든 요청/응답의 access 로그를 구조화 로그로 남긴다."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            log.info(
                "http_access",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration_ms, 2),
                client=request.client.host if request.client else None,
            )
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            log.exception(
                "http_error",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """슬라이딩 윈도우 RateLimit.

    `docs/24_api_response_spec.md` §11 정책:
      - /auth/*       : 1분 10회 / IP
      - /stocks /indicators ... 시세성: 1초 10회 / 사용자(or IP)
      - /orders POST  : 1초 3회, 일 1,000건 / 사용자
      - 그 외       : 1분 600회 / 사용자

    구현은 Redis ZSET을 사용한 슬라이딩 윈도우.
    """

    AUTH_PREFIX = "/api/v1/auth"
    ORDERS_POST = "/api/v1/orders"

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        # 헬스체크/docs는 면제
        if path in ("/healthz", "/readyz") or path.startswith("/docs") or path.startswith(
            "/openapi"
        ):
            return await call_next(request)

        identifier = self._identifier(request)

        # 정책 선택
        if path.startswith(self.AUTH_PREFIX):
            window_sec, limit = 60, settings.RATE_LIMIT_AUTH_PER_MIN
            bucket = f"auth:{identifier}"
        elif path == self.ORDERS_POST and request.method == "POST":
            window_sec, limit = 1, settings.RATE_LIMIT_ORDER_PER_SEC
            bucket = f"order:{identifier}"
        elif any(path.startswith(p) for p in ("/api/v1/stocks", "/api/v1/indicators")):
            window_sec, limit = 1, settings.RATE_LIMIT_QUOTE_PER_SEC
            bucket = f"quote:{identifier}"
        else:
            window_sec, limit = 60, settings.RATE_LIMIT_DEFAULT_PER_MIN
            bucket = f"default:{identifier}"

        allowed, remaining, reset_at = await self._slide_check(bucket, window_sec, limit)

        if not allowed:
            retry_after = max(1, reset_at - int(time.time()))
            return error_response(
                code="E0008",
                message="요청이 너무 많습니다.",
                details={"limit": limit, "window_sec": window_sec},
                http_status=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response

    def _identifier(self, request: Request) -> str:
        """식별자: Authorization 토큰 sub > 클라이언트 IP."""
        # 단순 식별자 (정밀한 사용자 추출은 인증 통과 후에야 가능)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # 토큰 자체로 식별 (해시 short)
            import hashlib
            return "u:" + hashlib.sha256(auth.encode()).hexdigest()[:16]
        client = request.client.host if request.client else "anon"
        return f"ip:{client}"

    async def _slide_check(
        self, bucket: str, window_sec: int, limit: int
    ) -> tuple[bool, int, int]:
        """슬라이딩 윈도우 체크. (allowed, remaining, reset_at_epoch)"""
        try:
            redis = get_redis()
            now_ms = int(time.time() * 1000)
            window_ms = window_sec * 1000
            key = f"rl:{bucket}"

            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, now_ms - window_ms)
            pipe.zadd(key, {f"{now_ms}-{uuid4().hex[:6]}": now_ms})
            pipe.zcard(key)
            pipe.expire(key, window_sec + 1)
            _, _, count, _ = await pipe.execute()

            remaining = max(0, limit - int(count))
            reset_at = int((now_ms + window_ms) / 1000)
            return (int(count) <= limit, remaining, reset_at)
        except Exception:
            # Redis 장애 시 차단하지 않는다 (graceful degrade)
            log.warning("ratelimit_redis_unavailable", bucket=bucket)
            return (True, limit, int(time.time()) + window_sec)
