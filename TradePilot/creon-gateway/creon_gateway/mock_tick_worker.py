"""Mock 모드용 가짜 tick 발행 워커.

실제 CREON COM 콜백이 없는 환경(개발/CI/Linux)에서 ``/ws/market`` E2E 검증을 위해
구독된 종목에 대해 1초 주기로 가짜 tick을 ``tp:market.tick.<code>`` 채널로 발행한다.

활성화 조건:
- ``MOCK_TICK_ENABLED=true`` (env)
- 어댑터가 ``MockCreonAdapter`` 인 경우에만 실행
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

import structlog

from creon_gateway.config import get_settings
from creon_gateway.creon_adapter import MockCreonAdapter, get_adapter
from creon_gateway.event_publisher import publish_tick

log = structlog.get_logger(__name__)


class MockTickWorker:
    """주기적으로 mock tick 발행."""

    def __init__(self, *, interval_sec: float = 1.0, default_codes: list[str] | None = None) -> None:
        self.interval_sec = interval_sec
        # 데모/테스트용 기본 종목
        self.default_codes = default_codes or ["005930", "000660", "035420", "035720"]
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._last_prices: dict[str, float] = {}

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        adapter = get_adapter()
        if not isinstance(adapter, MockCreonAdapter):
            log.info("mock_tick_skip_real_adapter")
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="mock-tick-worker")
        log.info("mock_tick_worker_started", interval_sec=self.interval_sec)

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
                # 어댑터에 등록된 구독 종목 + 기본 종목
                subscribed = list(getattr(adapter, "_tick_callbacks", {}).keys())
                codes = list({*self.default_codes, *subscribed})
                for code in codes:
                    base = self._last_prices.get(code) or adapter.get_quote(code).price
                    # 작은 노이즈 (-0.3% ~ +0.3%)
                    drift = base * random.uniform(-0.003, 0.003)
                    new_price = max(100.0, round(base + drift, 0))
                    change = new_price - base
                    change_pct = (change / base * 100.0) if base else 0.0
                    self._last_prices[code] = new_price
                    await publish_tick(
                        code=code,
                        price=new_price,
                        volume=random.randint(100, 5000),
                        change=change,
                        change_pct=round(change_pct, 3),
                        ts=datetime.now(tz=timezone.utc).isoformat(),
                    )
            except Exception:
                log.exception("mock_tick_iteration_error")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.interval_sec
                )
            except asyncio.TimeoutError:
                continue


_worker: MockTickWorker | None = None


def get_mock_tick_worker() -> MockTickWorker:
    global _worker
    if _worker is None:
        s = get_settings()
        interval = float(getattr(s, "MOCK_TICK_INTERVAL_SEC", 1.0))
        _worker = MockTickWorker(interval_sec=interval)
    return _worker
