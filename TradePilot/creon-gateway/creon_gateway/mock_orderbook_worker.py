"""Mock 모드용 가짜 호가창 발행 워커.

실제 CREON `StockJpBid` 콜백이 없는 환경(개발/CI/Linux)에서 ``/ws/orderbook``
E2E 검증을 위해 1초 주기로 가짜 호가창을 ``tp:market.orderbook.<code>``
채널로 발행한다.

활성화 조건:
- ``MOCK_TICK_ENABLED=true`` (env, 시세 worker와 동일 플래그 재사용)
- 어댑터가 ``MockCreonAdapter`` 인 경우에만 실행

설계 메모:
- 같은 종목이라도 잔량은 시간에 따라 deterministic하게 흔들리도록 한다.
- 시세 worker와 동일한 기본 종목(005930 등)을 발행해 차트 페이지 진입 시
  즉시 호가창이 보이도록 한다.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

import structlog

from creon_gateway.config import get_settings
from creon_gateway.creon_adapter import MockCreonAdapter, _calc_tick_size, get_adapter
from creon_gateway.event_publisher import publish_orderbook

log = structlog.get_logger(__name__)


class MockOrderbookWorker:
    """주기적으로 mock 호가창 발행.

    - 게이트웨이 라이프사이클에서 start/stop.
    - 어댑터의 ``_orderbook_callbacks`` 및 ``_tick_callbacks``의 키를 합집합으로
      구독 종목 후보에 포함시킨다 (시세 구독 중이면 호가도 보낸다).
    """

    def __init__(
        self,
        *,
        interval_sec: float = 1.0,
        default_codes: list[str] | None = None,
    ) -> None:
        self.interval_sec = interval_sec
        # 데모/테스트용 기본 종목 - 시세 worker와 동일
        self.default_codes = default_codes or [
            "005930",
            "000660",
            "035420",
            "035720",
        ]
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        # 종목별 기준가 추적 (호가 단위만큼 천천히 흔들어 보이게)
        self._base_prices: dict[str, float] = {}

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        adapter = get_adapter()
        if not isinstance(adapter, MockCreonAdapter):
            log.info("mock_orderbook_skip_real_adapter")
            return
        self._stop.clear()
        self._task = asyncio.create_task(
            self._run(), name="mock-orderbook-worker"
        )
        log.info(
            "mock_orderbook_worker_started", interval_sec=self.interval_sec
        )

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
                # 시세/호가 구독 종목 + 기본 종목
                tick_subs = set(getattr(adapter, "_tick_callbacks", {}).keys())
                ob_subs = set(getattr(adapter, "_orderbook_callbacks", {}).keys())
                codes = list({*self.default_codes, *tick_subs, *ob_subs})
                for code in codes:
                    await self._emit_one(code)
            except Exception:
                log.exception("mock_orderbook_iteration_error")
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.interval_sec
                )
            except asyncio.TimeoutError:
                continue

    async def _emit_one(self, code: str) -> None:
        adapter = get_adapter()
        # 기준가 - 시세 worker가 발행한 마지막 가격 추세 따라가지만
        # 호가는 시세와 다른 흔들림을 갖도록 자체 추적도 한다.
        base = self._base_prices.get(code) or adapter.get_quote(code).price
        tick = _calc_tick_size(base)
        # 작은 변동 (-1 ~ +1 tick) - 시드는 시간 기반
        drift = random.choice([-tick, 0, 0, 0, tick])
        new_base = max(100.0, base + drift)
        self._base_prices[code] = new_base

        # 잔량은 시간 기반 변동으로 deterministic이지만 보이는 흔들림이 있게
        bids: list[tuple[float, int]] = []
        asks: list[tuple[float, int]] = []
        for i in range(10):
            level = i + 1
            bid_price = max(1.0, round(new_base - tick * level))
            ask_price = round(new_base + tick * level)
            # 1단계 호가에 잔량이 가장 큼 (지수 감소 + 노이즈)
            base_qty = max(10, int(2000 * (1.0 - i * 0.07)))
            noise = random.randint(-base_qty // 5, base_qty // 5)
            bid_qty = max(1, base_qty + noise)
            ask_qty = max(1, base_qty + random.randint(-base_qty // 5, base_qty // 5))
            bids.append((bid_price, bid_qty))
            asks.append((ask_price, ask_qty))

        await publish_orderbook(
            stock_code=code,
            bids=bids,
            asks=asks,
            ts=datetime.now(tz=timezone.utc).isoformat(),
        )


_worker: MockOrderbookWorker | None = None


def get_mock_orderbook_worker() -> MockOrderbookWorker:
    global _worker
    if _worker is None:
        s = get_settings()
        interval = float(getattr(s, "MOCK_TICK_INTERVAL_SEC", 1.0))
        _worker = MockOrderbookWorker(interval_sec=interval)
    return _worker


def reset_mock_orderbook_worker() -> None:
    """테스트 격리용."""
    global _worker
    _worker = None
