"""SQLAlchemy 2.x 비동기 엔진/세션.

- `engine`: asyncpg 기반 AsyncEngine
- `AsyncSessionLocal`: async_sessionmaker
- `get_db()`: FastAPI 의존성. 요청 단위 세션을 yield 한다.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# 엔진 옵션: 풀 크기/오버플로우/echo 등
_ENGINE_KWARGS: dict[str, Any] = {
    "echo": settings.DB_ECHO,
    "pool_size": settings.DB_POOL_SIZE,
    "max_overflow": settings.DB_MAX_OVERFLOW,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_ENGINE_KWARGS)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 용 세션 제공자.

    예외 발생 시 자동 롤백, 항상 close. 명시적 commit/rollback은 서비스 계층 책임.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """애플리케이션 종료 시 호출하여 엔진 풀을 해제한다."""
    await engine.dispose()
