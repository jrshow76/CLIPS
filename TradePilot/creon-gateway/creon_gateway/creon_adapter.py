"""CREON COM 어댑터.

Windows 환경에서는 pywin32 + CREON COM 객체를 호출한다.
그 외(Linux/macOS) 환경에서는 자동으로 MockCreonAdapter로 fallback 한다 (개발/CI).

실제 COM 호출 메서드는 `docs/23_creon_gateway.md` §7.2 참고.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from creon_gateway.config import is_windows, settings

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# 데이터 클래스 (게이트웨이 내부 표현)
# ---------------------------------------------------------------------------
@dataclass
class OrderSubmitRequest:
    code: str
    side: str   # BUY | SELL
    qty: int
    order_type: str  # MARKET | LIMIT
    price: float | None = None
    account_no: str = ""
    account_kind: str = "01"


@dataclass
class OrderSubmitResponse:
    accepted: bool
    broker_order_no: str | None = None
    raw_code: int = 0
    raw_msg: str = ""


@dataclass
class CancelRequest:
    broker_order_no: str
    code: str
    qty: int = 0


@dataclass
class Balance:
    cash: float
    equity: float
    eval_amount: float


@dataclass
class PositionItem:
    code: str
    qty: int
    avg_price: float
    eval_pnl: float


@dataclass
class Quote:
    code: str
    price: float
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    ts: str = ""


# ---------------------------------------------------------------------------
# 추상 어댑터
# ---------------------------------------------------------------------------
class CreonAdapter:
    """CREON 어댑터 베이스."""

    def __init__(self) -> None:
        self.connected = False
        self.account_loaded = False
        self.last_check_at = 0.0

    def ensure_connected(self) -> None:
        """연결 확인 + 재연결."""
        raise NotImplementedError

    def submit_order(self, req: OrderSubmitRequest) -> OrderSubmitResponse:
        raise NotImplementedError

    def cancel_order(self, req: CancelRequest) -> OrderSubmitResponse:
        raise NotImplementedError

    def get_balance(self) -> Balance:
        raise NotImplementedError

    def get_positions(self) -> list[PositionItem]:
        raise NotImplementedError

    def get_quote(self, code: str) -> Quote:
        raise NotImplementedError

    def system_status(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "account_loaded": self.account_loaded,
            "last_check_at": self.last_check_at,
            "mode": "real" if isinstance(self, RealCreonAdapter) else "mock",
            "version": "1.0.0",
        }

    def reconnect(self) -> bool:
        self.ensure_connected()
        return self.connected


# ---------------------------------------------------------------------------
# Mock 어댑터 (개발/CI/비-Windows 환경)
# ---------------------------------------------------------------------------
class MockCreonAdapter(CreonAdapter):
    """COM 없이 동작하는 mock 구현. 모든 주문은 즉시 가상 체결."""

    def __init__(self) -> None:
        super().__init__()
        self._order_seq = 100000
        self._positions: dict[str, PositionItem] = {}
        self._cash = 100_000_000.0  # 1억원 가상 예수금
        self.connected = True
        self.account_loaded = True
        self.last_check_at = time.time()
        log.info("creon_adapter_mock_initialized")

    def ensure_connected(self) -> None:
        self.connected = True
        self.last_check_at = time.time()

    def submit_order(self, req: OrderSubmitRequest) -> OrderSubmitResponse:
        self.ensure_connected()
        # 데모 체결가
        quote = self.get_quote(req.code)
        fill_price = req.price or quote.price
        self._order_seq += 1
        bono = str(self._order_seq)

        # 포지션 갱신 (mock)
        if req.side == "BUY":
            cost = fill_price * req.qty
            if cost > self._cash:
                return OrderSubmitResponse(accepted=False, raw_code=-307, raw_msg="잔고부족")
            self._cash -= cost
            pos = self._positions.get(req.code)
            if pos:
                new_qty = pos.qty + req.qty
                pos.avg_price = ((pos.avg_price * pos.qty) + (fill_price * req.qty)) / new_qty
                pos.qty = new_qty
            else:
                self._positions[req.code] = PositionItem(
                    code=req.code, qty=req.qty, avg_price=fill_price, eval_pnl=0.0
                )
        else:  # SELL
            pos = self._positions.get(req.code)
            if not pos or pos.qty < req.qty:
                return OrderSubmitResponse(accepted=False, raw_code=-308, raw_msg="매도수량부족")
            self._cash += fill_price * req.qty
            pos.qty -= req.qty
            if pos.qty == 0:
                self._positions.pop(req.code, None)

        log.info(
            "mock_order_filled",
            code=req.code,
            side=req.side,
            qty=req.qty,
            price=fill_price,
            broker_order_no=bono,
        )
        return OrderSubmitResponse(accepted=True, broker_order_no=bono, raw_code=0, raw_msg="정상")

    def cancel_order(self, req: CancelRequest) -> OrderSubmitResponse:
        log.info("mock_order_canceled", broker_order_no=req.broker_order_no)
        return OrderSubmitResponse(accepted=True, raw_code=0, raw_msg="취소완료")

    def get_balance(self) -> Balance:
        equity = sum(p.qty * p.avg_price for p in self._positions.values())
        return Balance(cash=self._cash, equity=equity, eval_amount=self._cash + equity)

    def get_positions(self) -> list[PositionItem]:
        return list(self._positions.values())

    def get_quote(self, code: str) -> Quote:
        # 데모 가격 (각 종목 베이스 가격 + 작은 변동)
        base = 50000 + (hash(code) % 50000)
        price = float(base + random.randint(-200, 200))
        return Quote(code=code, price=price, change=0, change_pct=0, volume=1_000_000)


# ---------------------------------------------------------------------------
# 실제 COM 어댑터 (Windows + pywin32)
# ---------------------------------------------------------------------------
class RealCreonAdapter(CreonAdapter):
    """CREON COM 객체를 통해 실제 주문을 수행. Windows 전용."""

    def __init__(self) -> None:
        super().__init__()
        self._win32 = None
        self._cpcybos = None
        self._cptrade = None

        try:
            import pythoncom  # type: ignore[import-not-found]
            import win32com.client  # type: ignore[import-not-found]
            pythoncom.CoInitialize()
            self._win32 = win32com.client
        except Exception as e:
            log.error("pywin32_unavailable", error=str(e))
            raise

        self.ensure_connected()

    def ensure_connected(self) -> None:
        """CpCybos.IsConnect로 세션 확인 + 필요 시 재초기화."""
        try:
            cybos = self._win32.Dispatch("CpUtil.CpCybos")  # type: ignore[union-attr]
            self.connected = bool(cybos.IsConnect == 1)
            if self.connected:
                # 계좌 초기화 (CpTrade.CpTdUtil)
                trade_util = self._win32.Dispatch("CpTrade.CpTdUtil")  # type: ignore[union-attr]
                if trade_util.TradeInit(0) == 0:
                    self.account_loaded = True
            self.last_check_at = time.time()
        except Exception as e:
            log.exception("creon_ensure_connected_failed")
            self.connected = False
            self.account_loaded = False

    def submit_order(self, req: OrderSubmitRequest) -> OrderSubmitResponse:
        self.ensure_connected()
        if not self.connected:
            return OrderSubmitResponse(accepted=False, raw_code=-1, raw_msg="COM 미연결")
        try:
            obj = self._win32.Dispatch("CpTrade.CpTd0311")  # type: ignore[union-attr]
            obj.SetInputValue(0, "2" if req.side == "BUY" else "1")
            obj.SetInputValue(1, req.account_no or settings.CREON_ACCOUNT_NO)
            obj.SetInputValue(2, req.account_kind or settings.CREON_ACCOUNT_KIND)
            obj.SetInputValue(3, req.code)
            obj.SetInputValue(4, int(req.qty))
            obj.SetInputValue(5, int(req.price or 0))
            obj.SetInputValue(7, "0")
            obj.SetInputValue(8, "01" if req.order_type == "LIMIT" else "03")

            ret = obj.BlockRequest()
            if ret != 0:
                return OrderSubmitResponse(
                    accepted=False,
                    raw_code=obj.GetDibStatus(),
                    raw_msg=obj.GetDibMsg1(),
                )
            return OrderSubmitResponse(
                accepted=True,
                broker_order_no=str(obj.GetHeaderValue(8)),
                raw_code=0,
                raw_msg="정상",
            )
        except Exception as e:
            log.exception("creon_submit_failed")
            return OrderSubmitResponse(accepted=False, raw_code=-99, raw_msg=str(e))

    def cancel_order(self, req: CancelRequest) -> OrderSubmitResponse:
        self.ensure_connected()
        try:
            obj = self._win32.Dispatch("CpTrade.CpTd0314")  # type: ignore[union-attr]
            obj.SetInputValue(1, req.broker_order_no)
            obj.SetInputValue(2, settings.CREON_ACCOUNT_NO)
            obj.SetInputValue(3, settings.CREON_ACCOUNT_KIND)
            obj.SetInputValue(4, req.code)
            obj.SetInputValue(5, int(req.qty or 0))

            ret = obj.BlockRequest()
            if ret != 0:
                return OrderSubmitResponse(accepted=False, raw_code=ret, raw_msg="취소 실패")
            return OrderSubmitResponse(accepted=True, raw_code=0, raw_msg="취소완료")
        except Exception as e:
            log.exception("creon_cancel_failed")
            return OrderSubmitResponse(accepted=False, raw_code=-99, raw_msg=str(e))

    def get_balance(self) -> Balance:
        # 실제 CpTd6033 호출 구현은 운영 시점에 확장. v1.0 mock 값.
        return Balance(cash=0.0, equity=0.0, eval_amount=0.0)

    def get_positions(self) -> list[PositionItem]:
        return []

    def get_quote(self, code: str) -> Quote:
        try:
            obj = self._win32.Dispatch("Dscbo1.StockMst")  # type: ignore[union-attr]
            obj.SetInputValue(0, code)
            obj.BlockRequest()
            price = float(obj.GetHeaderValue(11))
            change = float(obj.GetHeaderValue(12))
            volume = int(obj.GetHeaderValue(18))
            return Quote(code=code, price=price, change=change, volume=volume)
        except Exception:
            log.exception("creon_quote_failed", code=code)
            return Quote(code=code, price=0.0)


# ---------------------------------------------------------------------------
# 팩토리
# ---------------------------------------------------------------------------
_adapter: CreonAdapter | None = None


def get_adapter() -> CreonAdapter:
    """싱글톤 어댑터.

    Windows + pywin32 사용 가능 + 강제 mock 비활성화 시 RealCreonAdapter,
    그 외 MockCreonAdapter.
    """
    global _adapter
    if _adapter is not None:
        return _adapter

    if settings.CREON_FORCE_MOCK or not is_windows():
        _adapter = MockCreonAdapter()
        return _adapter

    try:
        _adapter = RealCreonAdapter()
        log.info("creon_adapter_real_initialized")
    except Exception as e:
        log.warning("creon_adapter_fallback_to_mock", error=str(e))
        _adapter = MockCreonAdapter()
    return _adapter
