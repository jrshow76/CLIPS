"""크레온 게이트웨이 Redis Pub/Sub 리스너.

구독 채널 (docs/23 §6.1):
- tp:market.tick.{code}     : 실시간 시세
- tp:market.orderbook.{code}: 호가 변동
- tp:account.execution      : 체결 이벤트
- tp:account.order_update   : 주문 상태 변경
- tp:gateway.healthbeat     : 게이트웨이 헬스 (5초 주기)
- tp:gateway.alert          : 게이트웨이 경고

본 리스너는 백그라운드 태스크로 기동되며, 메시지를 적절한 핸들러로 디스패치한다.
체결 이벤트는 Celery 워커로 enqueue 한다.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import orjson
import structlog

from app.core.redis_client import get_redis

log = structlog.get_logger(__name__)


# 채널 prefix
CH_TICK = "tp:market.tick.*"
CH_ORDERBOOK = "tp:market.orderbook.*"
CH_EXECUTION = "tp:account.execution"
CH_ORDER_UPDATE = "tp:account.order_update"
CH_HEALTH = "tp:gateway.healthbeat"
CH_ALERT = "tp:gateway.alert"


# 게이트웨이 마지막 헬스비트 timestamp (메모리)
_last_healthbeat_at: float = 0.0


def get_last_healthbeat_at() -> float:
    """마지막 헬스비트 수신 시각 (epoch sec)."""
    return _last_healthbeat_at


def is_gateway_alive(threshold_sec: int = 15) -> bool:
    """게이트웨이가 살아있는지 판단. (`docs/23 §8.2`)"""
    return (time.time() - _last_healthbeat_at) < threshold_sec if _last_healthbeat_at else False


# ---------------------------------------------------------------------------
# 핸들러 타입
# ---------------------------------------------------------------------------
Handler = Callable[[str, dict[str, Any]], Awaitable[None]]


class CreonEventListener:
    """게이트웨이 Pub/Sub 리스너 (싱글톤)."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._handlers: dict[str, list[Handler]] = {}

    def on(self, channel_pattern: str, handler: Handler) -> None:
        """채널 패턴별 핸들러 등록."""
        self._handlers.setdefault(channel_pattern, []).append(handler)

    async def start(self) -> None:
        """리스너 시작."""
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="creon-event-listener")
        log.info("event_listener_started")

    async def stop(self) -> None:
        """리스너 정지."""
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        log.info("event_listener_stopped")

    async def _run(self) -> None:
        """메인 루프."""
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.psubscribe(
            CH_TICK, CH_ORDERBOOK, CH_EXECUTION, CH_ORDER_UPDATE, CH_HEALTH, CH_ALERT
        )
        log.info("event_listener_subscribed")

        try:
            while not self._stop.is_set():
                try:
                    msg = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                except Exception:
                    await asyncio.sleep(0.5)
                    continue
                if not msg:
                    continue
                await self._dispatch(msg)
        finally:
            await pubsub.aclose()

    async def _dispatch(self, msg: dict[str, Any]) -> None:
        """수신 메시지를 등록된 핸들러에 분배."""
        global _last_healthbeat_at

        channel = msg.get("channel") or msg.get("pattern") or ""
        if isinstance(channel, bytes):
            channel = channel.decode("utf-8")
        data_raw = msg.get("data")
        if isinstance(data_raw, bytes):
            data_raw = data_raw.decode("utf-8")
        try:
            payload = orjson.loads(data_raw) if isinstance(data_raw, str) else {}
        except Exception:
            payload = {"raw": data_raw}

        # 헬스비트 처리
        if channel == CH_HEALTH or channel.startswith("tp:gateway.healthbeat"):
            _last_healthbeat_at = time.time()
            log.debug("gateway_healthbeat", payload=payload)

        # 사용자 정의 핸들러
        for pattern, handlers in self._handlers.items():
            if _channel_match(channel, pattern):
                for h in handlers:
                    try:
                        await h(channel, payload)
                    except Exception:
                        log.exception("event_handler_error", channel=channel)


def _channel_match(channel: str, pattern: str) -> bool:
    """단순 와일드카드 매칭."""
    if "*" not in pattern:
        return channel == pattern
    return channel.startswith(pattern.split("*", 1)[0])


# 모듈 싱글톤
_listener: CreonEventListener | None = None


def get_event_listener() -> CreonEventListener:
    global _listener
    if _listener is None:
        _listener = CreonEventListener()
        _register_default_handlers(_listener)
    return _listener


def _register_default_handlers(listener: CreonEventListener) -> None:
    """기본 핸들러 등록."""

    async def on_execution(channel: str, payload: dict[str, Any]) -> None:
        """체결 이벤트 → Celery 워커로 위임."""
        log.info("execution_received", payload=payload)
        try:
            # 워커가 활성화된 경우에만 enqueue 시도
            from app.workers.celery_app import celery_app
            celery_app.send_task("orders.handle_execution", args=[payload], queue="orders")
        except Exception as e:
            log.warning("execution_enqueue_failed", error=str(e))

    async def on_order_update(channel: str, payload: dict[str, Any]) -> None:
        log.info("order_update_received", payload=payload)
        try:
            from app.workers.celery_app import celery_app
            celery_app.send_task("orders.handle_order_update", args=[payload], queue="orders")
        except Exception as e:
            log.warning("order_update_enqueue_failed", error=str(e))

    async def on_alert(channel: str, payload: dict[str, Any]) -> None:
        level = payload.get("level", "INFO")
        log.warning("gateway_alert", level=level, payload=payload)

    listener.on(CH_EXECUTION, on_execution)
    listener.on(CH_ORDER_UPDATE, on_order_update)
    listener.on(CH_ALERT, on_alert)
