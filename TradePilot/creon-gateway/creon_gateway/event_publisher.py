"""Redis Pub/Sub 발행기.

채널 (`docs/23 §6`):
- tp:market.tick.{code}     - 실시간 시세
- tp:market.orderbook.{code}- 호가
- tp:account.execution      - 체결
- tp:account.order_update   - 주문 상태 변경
- tp:gateway.healthbeat     - 헬스 (30초)
- tp:gateway.alert          - 경고
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import orjson
import redis.asyncio as aioredis
import structlog

from creon_gateway.config import settings

log = structlog.get_logger(__name__)


_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,
            health_check_interval=30,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def publish(channel: str, payload: dict[str, Any]) -> None:
    """단일 메시지 발행."""
    try:
        await get_redis().publish(channel, orjson.dumps(payload))
    except Exception:
        log.exception("publish_failed", channel=channel)


# ---------------------------------------------------------------------------
# 채널별 헬퍼
# ---------------------------------------------------------------------------
async def publish_tick(code: str, price: float, volume: int, **extra: Any) -> None:
    await publish(
        f"tp:market.tick.{code}",
        {
            "code": code,
            "price": price,
            "volume": volume,
            "source": "creon",
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            **extra,
        },
    )


async def publish_execution(payload: dict[str, Any]) -> None:
    await publish("tp:account.execution", payload)


async def publish_order_update(payload: dict[str, Any]) -> None:
    await publish("tp:account.order_update", payload)


async def publish_healthbeat(connected: bool, account_loaded: bool, subscribed: int = 0) -> None:
    await publish(
        "tp:gateway.healthbeat",
        {
            "gateway_id": settings.GATEWAY_ID,
            "com_connected": connected,
            "account_loaded": account_loaded,
            "subscribed_codes": subscribed,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


async def publish_alert(level: str, code: str, message: str, **extra: Any) -> None:
    await publish(
        "tp:gateway.alert",
        {
            "gateway_id": settings.GATEWAY_ID,
            "level": level,
            "code": code,
            "message": message,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            **extra,
        },
    )
