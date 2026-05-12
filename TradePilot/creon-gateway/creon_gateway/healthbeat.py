"""주기적 헬스비트 발행 백그라운드 태스크.

30초마다 `tp:gateway.healthbeat` 채널로 발행.
COM 단절 감지 시 자동 재연결 시도 (최대 3회).
"""
from __future__ import annotations

import asyncio

import structlog

from creon_gateway.config import settings
from creon_gateway.creon_adapter import get_adapter
from creon_gateway.event_publisher import publish_alert, publish_healthbeat

log = structlog.get_logger(__name__)

HEALTHBEAT_INTERVAL_SEC = 30


class HealthbeatTask:
    """백그라운드 헬스비트 태스크."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._reconnect_failures = 0

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="gateway-healthbeat")
        log.info("healthbeat_task_started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _run(self) -> None:
        adapter = get_adapter()
        while not self._stop.is_set():
            try:
                adapter.ensure_connected()
                if not adapter.connected:
                    self._reconnect_failures += 1
                    log.warning(
                        "creon_disconnected",
                        attempt=self._reconnect_failures,
                    )
                    if self._reconnect_failures >= settings.CREON_AUTO_RECONNECT_MAX:
                        await publish_alert(
                            level="CRITICAL",
                            code="G0002",
                            message=f"CREON 재연결 {settings.CREON_AUTO_RECONNECT_MAX}회 실패",
                        )
                else:
                    self._reconnect_failures = 0

                await publish_healthbeat(
                    connected=adapter.connected,
                    account_loaded=adapter.account_loaded,
                )
            except Exception:
                log.exception("healthbeat_iteration_failed")

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=HEALTHBEAT_INTERVAL_SEC)
            except asyncio.TimeoutError:
                pass


_singleton: HealthbeatTask | None = None


def get_healthbeat_task() -> HealthbeatTask:
    global _singleton
    if _singleton is None:
        _singleton = HealthbeatTask()
    return _singleton
