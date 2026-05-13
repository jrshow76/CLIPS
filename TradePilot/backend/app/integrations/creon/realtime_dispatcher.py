"""Redis Pub/Sub → WebSocket 디스패처.

이미 존재하는 ``CreonEventListener``는 체결을 Celery로 enqueue하는 역할 위주이고,
본 모듈은 **WebSocket 푸시 전용** 디스패처다.

구독 채널:
- ``tp:market.tick.*``           → market manager (종목별 broadcast)
- ``tp:account.execution``       → account manager (메시지 안의 user_id로 라우팅)
- ``tp:account.execution.<uid>`` → account manager (사용자 직지정)
- ``tp:notifications.<uid>``     → notifications manager (알림 서비스 publish)

FastAPI lifespan에서 start/stop.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import orjson
import structlog

from app.api.websocket.connection_manager import (
    get_account_manager,
    get_market_manager,
    get_notifications_manager,
)
from app.api.websocket.protocol import (
    ExecutionMessage,
    NotificationMessage,
    TickMessage,
)
from app.core.redis_client import get_redis

log = structlog.get_logger(__name__)


# 구독 패턴
PATTERN_TICK = "tp:market.tick.*"
PATTERN_EXECUTION = "tp:account.execution*"   # tp:account.execution + .<uid>
PATTERN_NOTIFICATION = "tp:notifications.*"


class RealtimeDispatcher:
    """Redis Pub/Sub 메시지를 WebSocket ConnectionManager로 디스패치."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._messages_total = 0
        self._last_tick_at: float = 0.0

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="realtime-dispatcher")
        log.info("realtime_dispatcher_started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        log.info(
            "realtime_dispatcher_stopped",
            messages_total=self._messages_total,
        )

    def stats(self) -> dict[str, Any]:
        return {
            "running": bool(self._task and not self._task.done()),
            "messages_total": self._messages_total,
            "last_tick_at": self._last_tick_at,
        }

    async def _run(self) -> None:
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.psubscribe(PATTERN_TICK, PATTERN_EXECUTION, PATTERN_NOTIFICATION)
        log.info(
            "realtime_dispatcher_subscribed",
            patterns=[PATTERN_TICK, PATTERN_EXECUTION, PATTERN_NOTIFICATION],
        )

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
                try:
                    await self._dispatch(msg)
                except Exception:
                    log.exception("realtime_dispatch_error")
        finally:
            try:
                await pubsub.punsubscribe()
            except Exception:
                pass
            await pubsub.aclose()

    async def _dispatch(self, msg: dict[str, Any]) -> None:
        channel = _decode(msg.get("channel"))
        data_raw = _decode(msg.get("data"))
        if data_raw is None:
            return
        try:
            payload: dict[str, Any] = orjson.loads(data_raw)
        except Exception:
            return
        self._messages_total += 1

        if channel.startswith("tp:market.tick."):
            await self._on_tick(channel, payload)
        elif channel.startswith("tp:account.execution"):
            await self._on_execution(channel, payload)
        elif channel.startswith("tp:notifications."):
            await self._on_notification(channel, payload)

    # ------------------------------------------------------------------
    # 핸들러
    # ------------------------------------------------------------------
    async def _on_tick(self, channel: str, payload: dict[str, Any]) -> None:
        # 채널 suffix가 종목 코드 (게이트웨이 발행 규약)
        stock_code = channel.split("tp:market.tick.", 1)[-1]
        # payload 안 code가 있으면 우선
        stock_code = str(payload.get("code") or stock_code)
        if not stock_code:
            return
        self._last_tick_at = time.monotonic()

        message = TickMessage(
            stock_code=stock_code,
            price=float(payload.get("price", 0.0) or 0.0),
            volume=int(payload.get("volume", 0) or 0),
            change=float(payload.get("change", 0.0) or 0.0),
            change_pct=float(payload.get("change_pct", 0.0) or 0.0),
            ts=str(payload.get("ts") or "") or TickMessage().ts,
        )
        manager = get_market_manager()
        await manager.broadcast_to_stock_subscribers(stock_code, message.model_dump())

    async def _on_execution(self, channel: str, payload: dict[str, Any]) -> None:
        # user_id 결정: 채널 suffix > payload.user_id
        suffix_uid = ""
        if channel != "tp:account.execution" and channel.startswith(
            "tp:account.execution."
        ):
            suffix_uid = channel.split("tp:account.execution.", 1)[-1]
        user_id = str(payload.get("user_id") or suffix_uid or "")
        if not user_id:
            log.warning("execution_missing_user_id", channel=channel)
            return

        message = ExecutionMessage(
            order_id=str(payload.get("order_id") or "") or None,
            broker_order_no=str(payload.get("broker_order_no") or "") or None,
            stock_code=str(payload.get("code") or payload.get("stock_code") or ""),
            side=str(payload.get("side", "BUY")).upper(),  # type: ignore[arg-type]
            qty=int(payload.get("qty", 0) or 0),
            price=float(payload.get("price", 0.0) or 0.0),
            ts=str(payload.get("ts") or "") or ExecutionMessage(
                stock_code="", side="BUY", qty=0, price=0.0
            ).ts,
        )
        manager = get_account_manager()
        await manager.send_to_user(user_id, message.model_dump())

    async def _on_notification(self, channel: str, payload: dict[str, Any]) -> None:
        suffix_uid = channel.split("tp:notifications.", 1)[-1]
        user_id = str(payload.get("user_id") or suffix_uid or "")
        if not user_id:
            return
        message = NotificationMessage(
            notification_id=payload.get("notification_id"),
            title=str(payload.get("title", "알림")),
            body=payload.get("body"),
            severity=str(payload.get("severity", "INFO")).upper(),  # type: ignore[arg-type]
            event_type=payload.get("event_type"),
            payload=dict(payload.get("payload") or {}),
            ts=str(payload.get("ts") or "") or NotificationMessage(title="").ts,
        )
        manager = get_notifications_manager()
        await manager.send_to_user(user_id, message.model_dump())


def _decode(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    return str(v)


# ---------------------------------------------------------------------------
# 싱글톤
# ---------------------------------------------------------------------------
_dispatcher: RealtimeDispatcher | None = None


def get_realtime_dispatcher() -> RealtimeDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = RealtimeDispatcher()
    return _dispatcher


def reset_realtime_dispatcher() -> None:
    """테스트 전용."""
    global _dispatcher
    _dispatcher = None
