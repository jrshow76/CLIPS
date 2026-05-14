"""키움 OpenAPI+ 어댑터.

Windows + pywin32 + PyQt5(QAxWidget) 환경에서는 ``KHOPENAPI.KHOpenAPICtrl.1`` OCX 를
호스팅하여 실제 키움 API 를 호출한다. 그 외 환경에서는 ``MockKiwoomAdapter`` 로 fallback.

키움 OpenAPI+ 의 주요 메서드 (참고):
- ``CommConnect()``: 로그인 윈도우 호출
- ``GetLoginInfo("ACCNO")``: 계좌 목록 반환 (";" 구분)
- ``SendOrder(rqname, scrno, accno, ordertype, code, qty, price, hoga, orgno)``
    * ordertype: 1=신규매수, 2=신규매도, 3=매수취소, 4=매도취소
    * hoga: "00"=지정가, "03"=시장가
- ``CommRqData(rqname, trcode, prevNext, scrno)`` + ``OnReceiveTrData`` 이벤트
- ``SetRealReg(scrno, codeList, fidList, optType)``  + ``OnReceiveRealData`` 이벤트

본 구현은 CREON 게이트웨이와 같이:
- 어댑터 베이스 + Mock + Real 분리
- RateLimiter (sliding window 1초)
- 표준 에러 코드 매핑 (키움 raw → K0xxx)
"""
from __future__ import annotations

import random
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

from kiwoom_gateway.config import get_settings, is_windows


def _settings():
    return get_settings()


log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------
@dataclass
class OrderSubmitRequest:
    code: str
    side: str             # BUY | SELL
    qty: int
    order_type: str       # MARKET | LIMIT
    price: float | None = None
    account_no: str = ""


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
    side: str = "BUY"   # 매수취소 / 매도취소 결정


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
# 키움 raw 코드 → 게이트웨이 K0xxx 매핑
# 키움 SendOrder 반환값: 0=정상, 그 외 음수 코드
# ---------------------------------------------------------------------------
KIWOOM_TO_GATEWAY_CODE: dict[int, str] = {
    0: "OK",
    -10: "K0001",   # 미접속
    -11: "K0001",   # 시세 미수신 (연결문제)
    -100: "K0001",  # 사용자 정보 미발급
    -101: "K0002",  # 서버 접속 실패
    -200: "K0010",  # 시세과부하 (호출제한)
    -201: "K0011",  # 주문가격 오류
    -202: "K0012",  # 주문수량 오류
    -300: "K0013",  # 주문 입력 오류
    -301: "K0014",  # 계좌 비밀번호 오류
}


def map_kiwoom_code(raw_code: int) -> str:
    """키움 raw 코드 → K0xxx 매핑."""
    return KIWOOM_TO_GATEWAY_CODE.get(raw_code, "K0010")


# ---------------------------------------------------------------------------
# RateLimiter (1초 sliding window)
# ---------------------------------------------------------------------------
class RateLimiter:
    """단순 sliding window — 키움 초당 호출 제한 보호."""

    def __init__(self, per_sec: int | None = None) -> None:
        self.per_sec = per_sec or _settings().RATE_LIMIT_PER_SEC
        self._ts: deque[float] = deque(maxlen=self.per_sec * 4)
        self._lock = threading.Lock()

    def acquire(self) -> float:
        wait_total = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                while self._ts and (now - self._ts[0]) > 1.0:
                    self._ts.popleft()
                if len(self._ts) < self.per_sec:
                    self._ts.append(now)
                    return wait_total
                sleep_for = 1.0 - (now - self._ts[0]) + 0.005
            sleep_for = max(sleep_for, 0.01)
            wait_total += sleep_for
            time.sleep(sleep_for)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            now = time.monotonic()
            return {"per_sec": sum(1 for t in self._ts if (now - t) <= 1.0)}


# ---------------------------------------------------------------------------
# 추상 어댑터
# ---------------------------------------------------------------------------
class KiwoomAdapter:
    """키움 어댑터 베이스 클래스."""

    def __init__(self) -> None:
        self.connected = False
        self.account_loaded = False
        self.last_check_at = 0.0
        self.last_error: str = ""
        self._rate_limiter = RateLimiter()
        self._tick_callbacks: dict[str, list[Callable[[Quote], None]]] = {}

    def ensure_connected(self) -> None:
        raise NotImplementedError

    def initialize_trade(self) -> bool:
        raise NotImplementedError

    def get_accounts(self) -> list[dict[str, Any]]:
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

    def subscribe_realtime(
        self, codes: list[str], callback: Callable[[Quote], None] | None = None
    ) -> int:
        raise NotImplementedError

    def unsubscribe_realtime(self, codes: list[str]) -> int:
        raise NotImplementedError

    # 공통 헬퍼
    def system_status(self) -> dict[str, Any]:
        snap = self._rate_limiter.snapshot()
        return {
            "connected": self.connected,
            "account_loaded": self.account_loaded,
            "last_check_at": self.last_check_at,
            "trade_env": _settings().KIWOOM_TRADE_ENV,
            "mode": "real" if isinstance(self, RealKiwoomAdapter) else "mock",
            "request_count_1s": snap["per_sec"],
            "rate_limit_per_sec": _settings().RATE_LIMIT_PER_SEC,
            "last_error": self.last_error,
            "version": "1.0.0",
        }

    def reconnect(self) -> bool:
        self.ensure_connected()
        return self.connected


# ---------------------------------------------------------------------------
# Mock 어댑터
# ---------------------------------------------------------------------------
class MockKiwoomAdapter(KiwoomAdapter):
    """OCX 없이 동작하는 mock 구현 (CI / Linux 운영자 테스트)."""

    def __init__(self) -> None:
        super().__init__()
        self._order_seq = 200000
        self._positions: dict[str, PositionItem] = {}
        self._cash = 100_000_000.0
        self.connected = True
        self.account_loaded = True
        self.last_check_at = time.time()
        log.info(
            "kiwoom_adapter_mock_initialized",
            trade_env=_settings().KIWOOM_TRADE_ENV,
        )

    def ensure_connected(self) -> None:
        self.connected = True
        self.last_check_at = time.time()

    def initialize_trade(self) -> bool:
        self.account_loaded = True
        return True

    def get_accounts(self) -> list[dict[str, Any]]:
        return [
            {
                "account_no": "8012345678" if _settings().is_sim_mode() else "0012345678",
                "name": "주식",
                "trade_env": _settings().KIWOOM_TRADE_ENV,
            }
        ]

    def submit_order(self, req: OrderSubmitRequest) -> OrderSubmitResponse:
        self._rate_limiter.acquire()
        quote = self.get_quote(req.code)
        fill_price = req.price or quote.price
        self._order_seq += 1
        bono = str(self._order_seq)

        if req.side == "BUY":
            cost = fill_price * req.qty
            if cost > self._cash:
                self.last_error = "예수금 부족"
                return OrderSubmitResponse(
                    accepted=False, raw_code=-201, raw_msg="예수금부족"
                )
            self._cash -= cost
            pos = self._positions.get(req.code)
            if pos:
                new_qty = pos.qty + req.qty
                pos.avg_price = (
                    (pos.avg_price * pos.qty) + (fill_price * req.qty)
                ) / new_qty
                pos.qty = new_qty
            else:
                self._positions[req.code] = PositionItem(
                    code=req.code, qty=req.qty, avg_price=fill_price, eval_pnl=0.0
                )
        else:
            pos = self._positions.get(req.code)
            if not pos or pos.qty < req.qty:
                self.last_error = "매도수량 부족"
                return OrderSubmitResponse(
                    accepted=False, raw_code=-202, raw_msg="매도수량부족"
                )
            self._cash += fill_price * req.qty
            pos.qty -= req.qty
            if pos.qty == 0:
                self._positions.pop(req.code, None)

        log.info(
            "kiwoom_mock_order_filled",
            code=req.code,
            side=req.side,
            qty=req.qty,
            price=fill_price,
            broker_order_no=bono,
        )
        return OrderSubmitResponse(
            accepted=True, broker_order_no=bono, raw_code=0, raw_msg="정상"
        )

    def cancel_order(self, req: CancelRequest) -> OrderSubmitResponse:
        self._rate_limiter.acquire()
        log.info("kiwoom_mock_order_canceled", broker_order_no=req.broker_order_no)
        return OrderSubmitResponse(accepted=True, raw_code=0, raw_msg="취소완료")

    def get_balance(self) -> Balance:
        equity = sum(p.qty * p.avg_price for p in self._positions.values())
        return Balance(
            cash=self._cash, equity=equity, eval_amount=self._cash + equity
        )

    def get_positions(self) -> list[PositionItem]:
        return list(self._positions.values())

    def get_quote(self, code: str) -> Quote:
        # 결정성을 위해 종목코드 해시 기반 가격
        base = 30000 + (hash(code) % 70000)
        price = float(base + random.randint(-150, 150))
        return Quote(
            code=code, price=price, change=0, change_pct=0, volume=500_000
        )

    def subscribe_realtime(
        self, codes: list[str], callback: Callable[[Quote], None] | None = None
    ) -> int:
        if callback:
            for c in codes:
                self._tick_callbacks.setdefault(c, []).append(callback)
        log.info("kiwoom_mock_subscribed", count=len(codes))
        return len(codes)

    def unsubscribe_realtime(self, codes: list[str]) -> int:
        for c in codes:
            self._tick_callbacks.pop(c, None)
        return len(codes)


# ---------------------------------------------------------------------------
# Real 어댑터 (Windows + pywin32 + PyQt5 QAxWidget)
# ---------------------------------------------------------------------------
class RealKiwoomAdapter(KiwoomAdapter):
    """키움 OpenAPI+ OCX 호스트 (Windows 전용).

    PyQt5 QAxWidget("KHOPENAPI.KHOpenAPICtrl.1") 로 OCX 를 호스팅한다.
    실제 구현은 별도 워커 프로세스에서 Qt 이벤트 루프와 통합되어야 한다
    (FastAPI 비동기 + Qt 이벤트 루프는 동일 프로세스에서 까다로움 — 본
    어댑터는 동기 메서드만 제공하고 호출은 별도 스레드에서 수행한다).
    """

    def __init__(self) -> None:
        super().__init__()
        self._ocx: Any = None
        try:
            # lazy import (Linux 환경에서는 import 자체가 실패하지 않게 한다)
            from PyQt5.QAxContainer import QAxWidget  # type: ignore[import-not-found]
            from PyQt5.QtWidgets import QApplication  # type: ignore[import-not-found]
            self._qt_app = QApplication.instance() or QApplication([])
            self._ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        except Exception as e:
            log.error("pyqt5_unavailable", error=str(e))
            raise

        self.ensure_connected()
        if self.connected:
            self.initialize_trade()

    def ensure_connected(self) -> None:
        """``GetConnectState()`` 가 1이면 연결됨."""
        try:
            state = int(self._ocx.dynamicCall("GetConnectState()"))
            self.connected = state == 1
            self.last_check_at = time.time()
            if not self.connected:
                self.last_error = "키움 미연결 (CommConnect 필요)"
        except Exception as e:  # noqa: BLE001
            log.exception("kiwoom_ensure_connected_failed")
            self.connected = False
            self.last_error = f"OCX dispatch 실패: {e}"

    def initialize_trade(self) -> bool:
        """계좌 목록 로드."""
        try:
            acc_str = self._ocx.dynamicCall('GetLoginInfo(QString)', "ACCNO")
            accounts = [a for a in str(acc_str).split(";") if a]
            self.account_loaded = bool(accounts)
            log.info("kiwoom_trade_init_ok", accounts=len(accounts))
            return self.account_loaded
        except Exception as e:  # noqa: BLE001
            self.account_loaded = False
            self.last_error = f"GetLoginInfo 예외: {e}"
            log.exception("kiwoom_trade_init_exception")
            return False

    def get_accounts(self) -> list[dict[str, Any]]:
        try:
            acc_str = self._ocx.dynamicCall('GetLoginInfo(QString)', "ACCNO")
            return [
                {
                    "account_no": a,
                    "name": "주식",
                    "trade_env": _settings().KIWOOM_TRADE_ENV,
                }
                for a in str(acc_str).split(";")
                if a
            ]
        except Exception as e:  # noqa: BLE001
            self.last_error = f"계좌 조회 실패: {e}"
            return []

    def submit_order(self, req: OrderSubmitRequest) -> OrderSubmitResponse:
        self.ensure_connected()
        if not self.connected:
            return OrderSubmitResponse(
                accepted=False, raw_code=-10, raw_msg="미접속"
            )
        self._rate_limiter.acquire()
        try:
            # 1=신규매수, 2=신규매도
            order_type = 1 if req.side == "BUY" else 2
            # 00=지정가, 03=시장가
            hoga = "00" if req.order_type == "LIMIT" else "03"
            ret = int(self._ocx.dynamicCall(
                'SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)',
                ["TPORD", "0101", req.account_no or _settings().KIWOOM_ACCOUNT_NO,
                 order_type, req.code, int(req.qty),
                 int(req.price or 0), hoga, ""]
            ))
            if ret != 0:
                self.last_error = f"SendOrder 실패 raw={ret}"
                return OrderSubmitResponse(
                    accepted=False, raw_code=ret, raw_msg="키움 주문 거부"
                )
            # 키움은 SendOrder 가 0 반환 후 OnReceiveTrData / OnReceiveChejanData 로
            # 주문번호를 비동기 수신. 본 동기 메서드에서는 broker_order_no 미확정.
            return OrderSubmitResponse(
                accepted=True, broker_order_no=None, raw_code=0, raw_msg="정상"
            )
        except Exception as e:  # noqa: BLE001
            self.last_error = f"주문 예외: {e}"
            log.exception("kiwoom_submit_failed")
            return OrderSubmitResponse(accepted=False, raw_code=-99, raw_msg=str(e))

    def cancel_order(self, req: CancelRequest) -> OrderSubmitResponse:
        self._rate_limiter.acquire()
        try:
            # 3=매수취소, 4=매도취소
            order_type = 3 if req.side == "BUY" else 4
            ret = int(self._ocx.dynamicCall(
                'SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)',
                ["TPCAN", "0102", _settings().KIWOOM_ACCOUNT_NO,
                 order_type, req.code, int(req.qty or 0), 0, "00", req.broker_order_no]
            ))
            if ret != 0:
                return OrderSubmitResponse(
                    accepted=False, raw_code=ret, raw_msg="취소 실패"
                )
            return OrderSubmitResponse(accepted=True, raw_code=0, raw_msg="취소완료")
        except Exception as e:  # noqa: BLE001
            log.exception("kiwoom_cancel_failed")
            return OrderSubmitResponse(accepted=False, raw_code=-99, raw_msg=str(e))

    def get_balance(self) -> Balance:
        # 실제 키움 잔고 조회는 OPW00004/OPW00018 TR 호출 + 비동기 이벤트로 수신.
        # 본 어댑터 v1 은 stub (운영 적용 시 별도 워커 구현 필요).
        return Balance(cash=0.0, equity=0.0, eval_amount=0.0)

    def get_positions(self) -> list[PositionItem]:
        return []

    def get_quote(self, code: str) -> Quote:
        # opt10001 TR. 비동기 이벤트 결합 필요 — v1 stub.
        return Quote(code=code, price=0.0)

    def subscribe_realtime(
        self, codes: list[str], callback: Callable[[Quote], None] | None = None
    ) -> int:
        if not codes:
            return 0
        try:
            # FID 10=현재가, 13=누적거래량
            self._ocx.dynamicCall(
                'SetRealReg(QString, QString, QString, QString)',
                ["1000", ";".join(codes), "10;13", "0"],
            )
            if callback:
                for c in codes:
                    self._tick_callbacks.setdefault(c, []).append(callback)
            return len(codes)
        except Exception:  # noqa: BLE001
            log.exception("kiwoom_subscribe_failed")
            return 0

    def unsubscribe_realtime(self, codes: list[str]) -> int:
        try:
            self._ocx.dynamicCall('SetRealRemove(QString, QString)', ["1000", ";".join(codes)])
            for c in codes:
                self._tick_callbacks.pop(c, None)
            return len(codes)
        except Exception:  # noqa: BLE001
            return 0


# ---------------------------------------------------------------------------
# 팩토리
# ---------------------------------------------------------------------------
_adapter: KiwoomAdapter | None = None


def get_adapter() -> KiwoomAdapter:
    """싱글톤. CREON 게이트웨이와 동일한 선택 규칙."""
    global _adapter
    if _adapter is not None:
        return _adapter

    if _settings().KIWOOM_FORCE_MOCK:
        _adapter = MockKiwoomAdapter()
        log.info("kiwoom_adapter_force_mock")
        return _adapter

    if not is_windows():
        _adapter = MockKiwoomAdapter()
        log.info("kiwoom_adapter_non_windows_mock")
        return _adapter

    if _settings().KIWOOM_USE_MOCK:
        _adapter = MockKiwoomAdapter()
        log.info("kiwoom_adapter_use_mock_true")
        return _adapter

    try:
        _adapter = RealKiwoomAdapter()
        log.info(
            "kiwoom_adapter_real_initialized",
            trade_env=_settings().KIWOOM_TRADE_ENV,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("kiwoom_adapter_fallback_to_mock", error=str(e))
        _adapter = MockKiwoomAdapter()
    return _adapter


def reset_adapter() -> None:
    """테스트용."""
    global _adapter
    _adapter = None
