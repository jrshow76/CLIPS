"""키움 게이트웨이 헬스비트 태스크.

CREON 게이트웨이와 동일한 패턴(주기적 healthbeat 발행 + 재연결 카운터).
"""
from __future__ import annotations

import asyncio

import structlog

from kiwoom_gateway.config import get_settings


def _settings():
    return get_settings()


from kiwoom_gateway.event_publisher import publish_alert, publish_healthbeat
from kiwoom_gateway.kiwoom_adapter import get_adapter

log = structlog.get_logger(__name__)


def _mask_account(acc: str) -> str:
    if not acc:
        return ""
    if len(acc) <= 4:
        return "*" * len(acc)
    return acc[:2] + "*" * (len(acc) - 4) + acc[-2:]


class HealthbeatTask:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._reconnect_failures = 0
        self._interval_sec = _settings().HEALTHBEAT_INTERVAL_SEC

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="kiwoom-healthbeat")
        log.info("kiwoom_healthbeat_started", interval_sec=self._interval_sec)

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
                        "kiwoom_disconnected",
                        attempt=self._reconnect_failures,
                    )
                    if self._reconnect_failures >= _settings().KIWOOM_AUTO_RECONNECT_MAX:
                        await publish_alert(
                            level="CRITICAL",
                            code="K0002",
                            message=(
                                f"키움 재연결 {_settings().KIWOOM_AUTO_RECONNECT_MAX}회 실패"
                            ),
                        )
                else:
                    self._reconnect_failures = 0

                status = adapter.system_status()
                await publish_healthbeat(
                    connected=adapter.connected,
                    account_loaded=adapter.account_loaded,
                    trade_env=_settings().KIWOOM_TRADE_ENV,
                    account_no_masked=_mask_account(_settings().KIWOOM_ACCOUNT_NO),
                    request_count_1s=status.get("request_count_1s", 0),
                    last_error=adapter.last_error,
                )
            except Exception:
                log.exception("kiwoom_healthbeat_iteration_failed")

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval_sec)
            except asyncio.TimeoutError:
                pass


_singleton: HealthbeatTask | None = None


def get_healthbeat_task() -> HealthbeatTask:
    global _singleton
    if _singleton is None:
        _singleton = HealthbeatTask()
    return _singleton


def reset_healthbeat_task() -> None:
    """테스트용."""
    global _singleton
    _singleton = None
