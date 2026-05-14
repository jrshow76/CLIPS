"""KillSwitchService 단위 테스트 — SEC-003(GATE-1).

DB/Redis 없이 mock 기반으로 핵심 보장사항을 검증한다:
1. LIVE 모드에서 라우터의 cancel_order가 **실제 호출**되는가
2. 5초 SLA 회로차단기가 동작하는가
3. 부분 실패 시 last_kill_switch_attempt_at / kill_switch_attempts 가 기록되는가
4. 부분 실패 시 E0015 가 raise 되며 details에 미처리 ID 가 포함되는가
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import AppException
from app.domains.ports.order_router_port import OrderResult


class _FakeAsyncSession:
    """SQLAlchemy AsyncSession 의 최소 mock.

    - execute(stmt): 등록된 응답을 차례로 반환
    - add(obj): 메모리에 보관
    - commit / rollback: no-op
    """

    def __init__(self, execute_results: list[Any]) -> None:
        self._results = list(execute_results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, stmt) -> Any:  # noqa: ANN001
        if self._results:
            return self._results.pop(0)
        # 빈 결과 mock
        m = MagicMock()
        m.scalars.return_value.all.return_value = []
        m.scalar_one_or_none.return_value = None
        m.scalar_one.return_value = 0
        return m

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass


def _scalars_result(items: list[Any]):
    """execute(stmt).scalars().all() 모킹용."""
    m = MagicMock()
    m.scalars.return_value.all.return_value = items
    return m


def _make_order(
    *,
    order_id: int = 1,
    trade_mode: str = "LIVE",
    status: str = "ACCEPTED",
    broker: str | None = "B-001",
    stock_id: int = 100,
) -> Any:
    """단순 Order namespace (속성 접근 가능, mutable)."""
    o = MagicMock()
    o.id = order_id
    o.public_id = uuid4()
    o.user_id = 1
    o.stock_id = stock_id
    o.trade_mode = trade_mode
    o.status = status
    o.broker_order_no = broker
    o.kill_switch_attempts = 0
    o.last_kill_switch_attempt_at = None
    o.canceled_at = None
    return o


def _make_stock(stock_id: int, code: str) -> Any:
    s = MagicMock()
    s.id = stock_id
    s.code = code
    return s


# ---------------------------------------------------------------------------
# 1) LIVE 모드: 라우터.cancel_order 가 실제 호출되어야 한다
# ---------------------------------------------------------------------------
def test_kill_switch_live_mode_invokes_router_cancel():
    """SEC-003: LIVE 모드 Kill Switch는 LiveOrderRouter.cancel_order를 호출해야 한다."""
    from app.services import kill_switch_service as ks_mod

    order = _make_order(trade_mode="LIVE", status="ACCEPTED")
    stock = _make_stock(100, "005930")

    db = _FakeAsyncSession(
        execute_results=[
            MagicMock(),  # 1) Strategy 비활성화 update
            _scalars_result([order]),  # 2) 활성 주문 조회
            _scalars_result([stock]),  # 3) 종목 매핑
            MagicMock(),  # 4) trade_mode 갱신
        ]
    )

    fake_router = MagicMock()
    fake_router.cancel_order = AsyncMock(
        return_value=OrderResult(
            accepted=True, status="CANCELED", broker_order_no="B-001"
        )
    )

    async def _run():
        with patch.object(ks_mod, "get_order_router", return_value=fake_router), patch.object(
            ks_mod, "get_redis", return_value=MagicMock(publish=AsyncMock())
        ):
            svc = ks_mod.KillSwitchService(db)
            result = await svc.trigger(
                user_id=1,
                trade_mode="LIVE",
                trigger_type="USER",
                reason="test",
            )
            return result

    result = asyncio.run(_run())

    # 핵심 검증: 라우터의 cancel_order 가 실제로 호출되었는가
    assert fake_router.cancel_order.await_count == 1
    call = fake_router.cancel_order.await_args
    # 위치 인자: order_id, broker_order_no, stock_code
    assert call.args[0] == 1
    assert call.args[1] == "B-001"
    assert call.args[2] == "005930"
    # 키워드 인자: timeout_sec + idempotency_key
    assert call.kwargs["timeout_sec"] is not None
    assert call.kwargs["idempotency_key"].startswith("killswitch:")
    # 결과: 1건 취소 성공
    assert len(result["canceled_orders"]) == 1
    assert result["failed"] == []
    assert result["mode_switched"] is True


# ---------------------------------------------------------------------------
# 2) SIM 모드: SimRouter.cancel_order 가 호출되며 mode_switched=False
# ---------------------------------------------------------------------------
def test_kill_switch_sim_mode_keeps_mode_and_uses_sim_router():
    """SIM 모드는 SimRouter를 통해 in-memory cancel하고 trade_mode는 그대로."""
    from app.services import kill_switch_service as ks_mod

    order = _make_order(trade_mode="SIM", status="NEW")
    stock = _make_stock(100, "035720")

    db = _FakeAsyncSession(
        execute_results=[
            MagicMock(),
            _scalars_result([order]),
            _scalars_result([stock]),
        ]
    )

    fake_router = MagicMock()
    fake_router.cancel_order = AsyncMock(
        return_value=OrderResult(accepted=True, status="CANCELED")
    )

    async def _run():
        with patch.object(ks_mod, "get_order_router", return_value=fake_router), patch.object(
            ks_mod, "get_redis", return_value=MagicMock(publish=AsyncMock())
        ):
            svc = ks_mod.KillSwitchService(db)
            return await svc.trigger(
                user_id=1, trade_mode="SIM", trigger_type="USER", reason="sim test"
            )

    result = asyncio.run(_run())
    assert fake_router.cancel_order.await_count == 1
    assert result["mode_switched"] is False  # SIM은 모드 전환 없음
    assert len(result["canceled_orders"]) == 1


# ---------------------------------------------------------------------------
# 3) 부분 실패: cancel_order 가 예외/거부 → E0015 + last_kill_switch_attempt_at 기록
# ---------------------------------------------------------------------------
def test_kill_switch_partial_failure_records_retry_metadata_and_raises_E0015():
    """SEC-003: 라우터 실패 주문은 attempts/last_attempt_at 갱신 + E0015 raise."""
    from app.services import kill_switch_service as ks_mod

    ok_order = _make_order(order_id=1, trade_mode="LIVE", broker="B-1", stock_id=100)
    bad_order = _make_order(order_id=2, trade_mode="LIVE", broker="B-2", stock_id=101)
    stock_a = _make_stock(100, "005930")
    stock_b = _make_stock(101, "035720")

    db = _FakeAsyncSession(
        execute_results=[
            MagicMock(),
            _scalars_result([ok_order, bad_order]),
            _scalars_result([stock_a, stock_b]),
            MagicMock(),
        ]
    )

    async def _cancel(order_id, broker, code, *, timeout_sec=None, idempotency_key=None):
        if order_id == 2:
            raise AppException("E0072", message="gateway timeout")
        return OrderResult(accepted=True, status="CANCELED", broker_order_no=broker)

    fake_router = MagicMock()
    fake_router.cancel_order = AsyncMock(side_effect=_cancel)

    async def _run():
        with patch.object(ks_mod, "get_order_router", return_value=fake_router), patch.object(
            ks_mod, "get_redis", return_value=MagicMock(publish=AsyncMock())
        ):
            svc = ks_mod.KillSwitchService(db)
            with pytest.raises(AppException) as ei:
                await svc.trigger(
                    user_id=1, trade_mode="LIVE", trigger_type="USER", reason="partial"
                )
            return ei.value

    err = asyncio.run(_run())
    assert err.code == "E0015"
    details = err.details or {}
    assert len(details["canceled_orders"]) == 1
    assert len(details["failed"]) == 1
    # 실패 주문에는 재시도 metadata 가 새겨져야 함
    assert bad_order.kill_switch_attempts == 1
    assert bad_order.last_kill_switch_attempt_at is not None
    # 성공 주문은 last_attempt_at = None (재시도 큐에서 제외)
    assert ok_order.last_kill_switch_attempt_at is None
    assert ok_order.status == "CANCELED"


# ---------------------------------------------------------------------------
# 4) SLA 5초: 남은 시간이 부족하면 회로차단되어 나머지는 모두 failed로 누적
# ---------------------------------------------------------------------------
def test_kill_switch_sla_circuit_breaker_marks_remaining_failed():
    """SEC-003: SLA 임박 시 남은 주문 처리 중단 + Redis publish."""
    from app.services import kill_switch_service as ks_mod

    orders = [
        _make_order(order_id=i, trade_mode="LIVE", broker=f"B-{i}", stock_id=100 + i)
        for i in range(1, 4)
    ]
    stocks = [_make_stock(100 + i, f"00000{i}") for i in range(1, 4)]

    db = _FakeAsyncSession(
        execute_results=[
            MagicMock(),
            _scalars_result(orders),
            _scalars_result(stocks),
            MagicMock(),
        ]
    )

    # cancel_order 가 호출될 때마다 3초 sleep → 첫 1건 만에 SLA 초과
    async def _slow_cancel(*args, **kwargs):
        await asyncio.sleep(3.0)
        return OrderResult(accepted=True, status="CANCELED")

    fake_router = MagicMock()
    fake_router.cancel_order = AsyncMock(side_effect=_slow_cancel)
    publish_mock = AsyncMock()

    async def _run():
        with patch.object(ks_mod, "get_order_router", return_value=fake_router), patch.object(
            ks_mod, "get_redis", return_value=MagicMock(publish=publish_mock)
        ), patch.object(ks_mod, "KILL_SWITCH_SLA_SEC", 2.5):
            svc = ks_mod.KillSwitchService(db)
            with pytest.raises(AppException) as ei:
                await svc.trigger(
                    user_id=1, trade_mode="LIVE", trigger_type="USER", reason="sla"
                )
            return ei.value

    started = time.monotonic()
    err = asyncio.run(_run())
    elapsed = time.monotonic() - started

    # 전체 절차는 SLA + cancel 1건 + 약간의 정리. 6초를 넘으면 안 됨
    assert elapsed < 6.0, f"Kill Switch overall took {elapsed:.1f}s"
    details = err.details or {}
    assert details["sla_violated"] is True
    # 최소 1건 이상 failed
    assert len(details["failed"]) >= 1
    # Redis publish 가 호출되어야 함 (부분 실패 이벤트)
    assert publish_mock.await_count >= 1
    channel = publish_mock.await_args.args[0]
    assert channel == "tp:gateway.killswitch_partial"


# ---------------------------------------------------------------------------
# 5) retry_failed_cancels: 부분 실패 주문 재시도가 동작하는가
# ---------------------------------------------------------------------------
def test_kill_switch_retry_failed_cancels_promotes_to_canceled():
    """재시도 워커가 부분 실패 주문을 라우터로 다시 cancel 처리한다."""
    from app.services import kill_switch_service as ks_mod

    pending = _make_order(order_id=10, trade_mode="LIVE", broker="B-10", stock_id=200)
    pending.kill_switch_attempts = 1
    pending.last_kill_switch_attempt_at = datetime.now(tz=timezone.utc)
    stock = _make_stock(200, "005930")

    db = _FakeAsyncSession(
        execute_results=[
            _scalars_result([pending]),  # 재시도 대상 조회
            _scalars_result([stock]),  # 종목 매핑
        ]
    )

    fake_router = MagicMock()
    fake_router.cancel_order = AsyncMock(
        return_value=OrderResult(accepted=True, status="CANCELED")
    )

    async def _run():
        with patch.object(ks_mod, "get_order_router", return_value=fake_router):
            svc = ks_mod.KillSwitchService(db)
            return await svc.retry_failed_cancels()

    result = asyncio.run(_run())
    assert result["retried"] == 1
    assert result["canceled"] == 1
    assert pending.status == "CANCELED"
    assert pending.last_kill_switch_attempt_at is None
