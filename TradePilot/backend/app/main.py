"""FastAPI 엔트리포인트.

- lifespan: Redis/Creon 클라이언트/이벤트 리스너 초기화 + 종료 정리
- 미들웨어: CORS, TraceId, RequestLogging, RateLimit
- 글로벌 예외 핸들러 등록
- /api/v1 라우터 통합
- /healthz, /readyz 헬스 엔드포인트
"""
from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import dispose_engine, engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    TraceIdMiddleware,
)
from app.core.redis_client import close_redis, get_redis, ping_redis

# 라우터 임포트는 lifespan 이후 (테스트 격리를 위함)
from app.api.v1 import register_v1_routers

log = get_logger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """애플리케이션 lifespan."""
    configure_logging()
    log.info(
        "app_startup",
        env=settings.APP_ENV,
        role=settings.SERVICE_ROLE,
        version="1.0.0",
    )

    # Redis 워밍업
    redis_ok = await ping_redis()
    log.info("redis_ping", ok=redis_ok)

    # 크레온 이벤트 리스너 (API/scheduler 역할에서만 기동, worker는 별도 기동)
    listener_task = None
    if settings.SERVICE_ROLE in ("api", "scheduler"):
        try:
            from app.integrations.creon.event_listener import get_event_listener
            listener = get_event_listener()
            await listener.start()
            listener_task = listener
        except Exception as e:
            log.warning("event_listener_start_failed", error=str(e))

    yield

    # 종료 정리
    log.info("app_shutdown")
    try:
        if listener_task:
            await listener_task.stop()
    except Exception:
        pass
    try:
        from app.integrations.creon.client import close_creon_client
        await close_creon_client()
    except Exception:
        pass
    await close_redis()
    await dispose_engine()


def create_app() -> FastAPI:
    """FastAPI 앱 팩토리."""
    app = FastAPI(
        title="TradePilot API",
        description="자동주식매매 시스템 TradePilot의 백엔드 API.",
        version="1.0.0",
        docs_url="/docs" if not settings.is_test else None,
        redoc_url="/redoc" if not settings.is_test else None,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    # 미들웨어 (실행 순서: 등록 역순으로 dispatch)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Trade-Mode",
            "X-Idempotency-Key",
            "X-Request-Id",
            "Accept-Language",
        ],
        expose_headers=[
            "X-Request-Id",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(TraceIdMiddleware)

    # 글로벌 예외 핸들러
    register_exception_handlers(app)

    # 헬스체크
    @app.get("/healthz", tags=["meta"], include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["meta"], include_in_schema=False)
    async def readyz() -> dict[str, object]:
        """DB / Redis / 게이트웨이 상태 종합."""
        from sqlalchemy import text

        db_ok = False
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            pass

        redis_ok = await ping_redis()

        # 크레온 게이트웨이는 헬스비트 기반 (없어도 ready로 간주)
        from app.integrations.creon.event_listener import is_gateway_alive
        gateway_alive = is_gateway_alive(threshold_sec=30)

        return {
            "ready": db_ok and redis_ok,
            "db": db_ok,
            "redis": redis_ok,
            "creon_gateway": gateway_alive,
        }

    # v1 라우터 통합
    v1_router = APIRouter(prefix=settings.API_V1_PREFIX)
    register_v1_routers(v1_router)
    app.include_router(v1_router)

    return app


app = create_app()
