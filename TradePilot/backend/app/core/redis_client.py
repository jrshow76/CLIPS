"""Redis 비동기 클라이언트.

- 캐시: REDIS_URL (db=0)
- 멱등성 키, Rate Limit 카운터, Pub/Sub 등 모두 본 클라이언트로 처리한다.
- creon-gateway와 동일 인스턴스를 공유한다(Pub/Sub 채널 `tp:*`).
"""
from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

# 모듈 전역 싱글톤 (FastAPI lifespan에서 close)
_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """싱글톤 Redis 클라이언트를 반환한다."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
    return _redis


async def close_redis() -> None:
    """애플리케이션 종료 시 호출."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def ping_redis() -> bool:
    """헬스체크 용도."""
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 캐시 유틸 (자주 쓰는 패턴 캡슐화)
# ---------------------------------------------------------------------------
async def cache_get_json(key: str) -> Any | None:
    import orjson

    raw = await get_redis().get(key)
    return orjson.loads(raw) if raw else None


async def cache_set_json(key: str, value: Any, ttl_sec: int) -> None:
    import orjson

    await get_redis().set(key, orjson.dumps(value), ex=ttl_sec)


async def cache_delete(key: str) -> None:
    await get_redis().delete(key)
