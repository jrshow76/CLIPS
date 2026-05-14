"""키움 게이트웨이 Redis Pub/Sub 발행기.

CREON 게이트웨이와 채널을 동일하게 사용한다 (본체에서 broker 라벨로 구분).
- tp:market.tick.{code}      - 실시간 시세
- tp:account.execution       - 체결
- tp:account.order_update    - 주문 상태 변경
- tp:gateway.healthbeat      - 헬스 (broker=kiwoom 라벨)
- tp:gateway.alert           - 경고
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import orjson
import redis.asyncio as aioredis
import structlog

from kiwoom_gateway.config import settings

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
    try:
        await get_redis().publish(channel, orjson.dumps(payload))
    except Exception:  # noqa: BLE001
        log.exception("publish_failed", channel=channel)


async def publish_tick(code: str, price: float, volume: int, **extra: Any) -> None:
    await publish(
        f"tp:market.tick.{code}",
        {
            "code": code,
            "price": price,
            "volume": volume,
            "source": "kiwoom",
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            **extra,
        },
    )


async def publish_execution(payload: dict[str, Any]) -> None:
    payload.setdefault("broker", "KIWOOM")
    await publish("tp:account.execution", payload)


async def publish_order_update(payload: dict[str, Any]) -> None:
    payload.setdefault("broker", "KIWOOM")
    await publish("tp:account.order_update", payload)


async def publish_healthbeat(
    connected: bool,
    account_loaded: bool,
    subscribed: int = 0,
    trade_env: str = "SIM",
    account_no_masked: str = "",
    request_count_1s: int = 0,
    last_error: str = "",
) -> None:
    await publish(
        "tp:gateway.healthbeat",
        {
            "gateway_id": settings.GATEWAY_ID,
            "broker": "KIWOOM",
            "trade_env": trade_env,
            "account_no_masked": account_no_masked,
            "connected": connected,
            "account_loaded": account_loaded,
            "subscribed_codes": subscribed,
            "request_count_1s": request_count_1s,
            "last_error": last_error,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        },
    )


async def publish_alert(level: str, code: str, message: str, **extra: Any) -> None:
    await publish(
        "tp:gateway.alert",
        {
            "gateway_id": settings.GATEWAY_ID,
            "broker": "KIWOOM",
            "level": level,
            "code": code,
            "message": message,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            **extra,
        },
    )
