"""CREON COM 어댑터.

Windows 환경에서는 pywin32 + CREON COM 객체를 호출한다.
그 외(Linux/macOS) 또는 pythoncom 미설치 환경에서는 자동으로 `MockCreonAdapter`로 fallback 한다.

본 어댑터는 다음 책임을 가진다.
1. CREON Plus 연결 및 자동 재연결 (`CpUtil.CpCybos`)
2. 거래 초기화 (`CpTrade.CpTdUtil.TradeInit`) + 비밀번호 검증
3. SIM(모의투자) / REAL(실거래) 계좌 필터링 (계좌 접두사 기반)
4. 요청 제한 슬라이딩 윈도우 (1초 12건 / 4초 48건, 안전 마진 80%)
5. 주문 / 취소 / 잔고 / 시세 / 종목마스터 / 실시간 구독
6. CREON 응답 코드를 게이트웨이 표준 에러 코드(G0xxx)로 매핑

자세한 설계: `docs/23_creon_gateway.md` §7.
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

from creon_gateway.config import get_settings, is_windows


def _settings():
    """호출 시점의 settings (테스트 reload 대응)."""
    return get_settings()

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


@dataclass
class OrderbookSnapshot:
    """호가창 스냅샷 (매수/매도 10단계).

    `bids`/`asks`는 가격이 좋은 순(매수=높은가, 매도=낮은가)으로 정렬된
    `[(price, qty), ...]` 형태. CREON `StockJpBid` 명세 §1단계~10단계 매핑.
    """

    code: str
    bids: list[tuple[float, int]]
    asks: list[tuple[float, int]]
    total_bid_qty: int = 0
    total_ask_qty: int = 0
    ts: str = ""


@dataclass
class StockMaster:
    code: str
    name: str
    market: str  # KOSPI | KOSDAQ
    sector: str = ""
    is_etf: bool = False
    is_suspended: bool = False
    upper_limit: float = 0.0
    lower_limit: float = 0.0


# ---------------------------------------------------------------------------
# 에러 코드 매핑 (CREON 원본 → 게이트웨이 표준 G코드)
# ---------------------------------------------------------------------------
# `docs/23_creon_gateway.md` §5.4 와 일치하도록 유지.
CREON_TO_GATEWAY_CODE: dict[int, str] = {
    0: "OK",
    -100: "G0001",  # 통신 실패
    -101: "G0002",  # 연결 단절
    -300: "G0010",  # 주문 일반 실패
    -307: "G0011",  # 잔고/증거금 부족
    -308: "G0011",  # 매도수량 부족
    -310: "G0012",  # 호가단위 오류
    -311: "G0013",  # 상하한가 도달
    -312: "G0014",  # 거래 정지
    -901: "G0020",  # 응답 타임아웃
    -902: "G0030",  # 시세 미수신
}


def map_creon_code(raw_code: int) -> str:
    """CREON 원본 코드를 게이트웨이 표준 코드(G0xxx)로 매핑."""
    return CREON_TO_GATEWAY_CODE.get(raw_code, "G0010")


def _calc_tick_size(price: float) -> float:
    """KRX 호가 단위 단순화.

    실제 호가 단위(2024 기준) 근사치 - 호가창 mock 생성용.
    """
    if price < 2000:
        return 1.0
    if price < 5000:
        return 5.0
    if price < 20000:
        return 10.0
    if price < 50000:
        return 50.0
    if price < 200000:
        return 100.0
    if price < 500000:
        return 500.0
    return 1000.0


# ---------------------------------------------------------------------------
# 요청 제한 (슬라이딩 윈도우: 1초 + 4초)
# ---------------------------------------------------------------------------
class RateLimiter:
    """CREON 요청 제한 슬라이딩 윈도우.

    - 1초 윈도우: `RATE_LIMIT_PER_SEC` (기본 12, 안전 마진 80%)
    - 4초 윈도우: `RATE_LIMIT_PER_4SEC` (기본 48, 안전 마진 80%)

    초과 시 가장 가까운 윈도우 만료 시점까지 sleep하여 자동 페이싱한다.
    스레드 안전.
    """

    def __init__(
        self,
        per_sec: int | None = None,
        per_4sec: int | None = None,
    ) -> None:
        self.per_sec = per_sec or _settings().RATE_LIMIT_PER_SEC
        self.per_4sec = per_4sec or _settings().RATE_LIMIT_PER_4SEC
        self._timestamps: deque[float] = deque(maxlen=max(self.per_4sec, 100))
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """요청 슬롯 확보. 대기한 시간(초)을 반환."""
        wait_total = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                # 4초 이내 타임스탬프만 유지
                while self._timestamps and (now - self._timestamps[0]) > 4.0:
                    self._timestamps.popleft()

                cnt_1s = sum(1 for t in self._timestamps if (now - t) <= 1.0)
                cnt_4s = len(self._timestamps)

                if cnt_1s < self.per_sec and cnt_4s < self.per_4sec:
                    self._timestamps.append(now)
                    return wait_total

                # 가장 가까운 만료 시점까지 sleep
                if cnt_1s >= self.per_sec:
                    # 1초 윈도우 만료를 기다린다
                    oldest_in_1s = next(
                        (t for t in self._timestamps if (now - t) <= 1.0), now
                    )
                    sleep_for = 1.0 - (now - oldest_in_1s) + 0.005
                else:
                    # 4초 윈도우 만료
                    sleep_for = 4.0 - (now - self._timestamps[0]) + 0.005

            sleep_for = max(sleep_for, 0.01)
            wait_total += sleep_for
            time.sleep(sleep_for)

    def snapshot(self) -> dict[str, int]:
        """현재 카운터 스냅샷 (메트릭/헬스용)."""
        with self._lock:
            now = time.monotonic()
            cnt_1s = sum(1 for t in self._timestamps if (now - t) <= 1.0)
            cnt_4s = sum(1 for t in self._timestamps if (now - t) <= 4.0)
            return {"per_sec": cnt_1s, "per_4sec": cnt_4s}


# ---------------------------------------------------------------------------
# 추상 어댑터
# ---------------------------------------------------------------------------
class CreonAdapter:
    """CREON 어댑터 베이스 클래스."""

    def __init__(self) -> None:
        self.connected = False
        self.account_loaded = False
        self.last_check_at = 0.0
        self.last_error: str = ""
        self._rate_limiter = RateLimiter()
        self._tick_callbacks: dict[str, list[Callable[[Quote], None]]] = {}
        # 호가 구독 콜백. 시세 구독과 분리해 관리한다.
        self._orderbook_callbacks: dict[
            str, list[Callable[[OrderbookSnapshot], None]]
        ] = {}

    # ---------------- 기본 인터페이스 ----------------
    def ensure_connected(self) -> None:
        raise NotImplementedError

    def initialize_trade(self) -> bool:
        """거래 초기화. 성공 시 True 반환."""
        raise NotImplementedError

    def get_accounts(self) -> list[dict[str, Any]]:
        """현재 모드(SIM/REAL)에 해당하는 계좌 목록."""
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

    def get_stock_master(self, code: str) -> StockMaster:
        raise NotImplementedError

    def subscribe_realtime(
        self, codes: list[str], callback: Callable[[Quote], None] | None = None
    ) -> int:
        """실시간 시세 구독. 구독된 종목 수 반환."""
        raise NotImplementedError

    def unsubscribe_realtime(self, codes: list[str]) -> int:
        raise NotImplementedError

    def subscribe_orderbook(
        self,
        codes: list[str],
        callback: Callable[[OrderbookSnapshot], None] | None = None,
    ) -> int:
        """실시간 호가 (StockJpBid) 구독. 구독된 종목 수 반환."""
        raise NotImplementedError

    def unsubscribe_orderbook(self, codes: list[str]) -> int:
        raise NotImplementedError

    def get_orderbook(self, code: str) -> OrderbookSnapshot:
        """호가 스냅샷 1회 조회 (StockJpBid BlockRequest)."""
        raise NotImplementedError

    # ---------------- 공통 헬퍼 ----------------
    def request_with_rate_limit(self, method: Callable, *args, **kwargs) -> Any:
        """요청 제한 슬라이딩 윈도우를 적용해 메서드 호출."""
        self._rate_limiter.acquire()
        return method(*args, **kwargs)

    def system_status(self) -> dict[str, Any]:
        snap = self._rate_limiter.snapshot()
        return {
            "connected": self.connected,
            "account_loaded": self.account_loaded,
            "last_check_at": self.last_check_at,
            "trade_env": _settings().CREON_TRADE_ENV,
            "mode": "real" if isinstance(self, RealCreonAdapter) else "mock",
            "request_count_1s": snap["per_sec"],
            "request_count_4s": snap["per_4sec"],
            "rate_limit_per_sec": _settings().RATE_LIMIT_PER_SEC,
            "rate_limit_per_4sec": _settings().RATE_LIMIT_PER_4SEC,
            "last_error": self.last_error,
            "version": "1.0.0",
        }

    def reconnect(self) -> bool:
        self.ensure_connected()
        return self.connected


# ---------------------------------------------------------------------------
# Mock 어댑터 (개발/CI/비-Windows 환경)
# ---------------------------------------------------------------------------
class MockCreonAdapter(CreonAdapter):
    """COM 없이 동작하는 mock 구현.

    - 모든 주문은 즉시 가상 체결 (체결가 = 지정가 또는 mock quote)
    - 결정성(deterministic)을 위해 종목 코드 해시 기반 가격
    - SIM 모드에서는 모의 계좌 1개, REAL 모드에서는 실계좌 1개를 반환
    """

    def __init__(self) -> None:
        super().__init__()
        self._order_seq = 100000
        self._positions: dict[str, PositionItem] = {}
        self._cash = 100_000_000.0  # 1억원 가상 예수금
        self.connected = True
        self.account_loaded = True
        self.last_check_at = time.time()
        log.info(
            "creon_adapter_mock_initialized",
            trade_env=_settings().CREON_TRADE_ENV,
        )

    def ensure_connected(self) -> None:
        self.connected = True
        self.last_check_at = time.time()

    def initialize_trade(self) -> bool:
        self.account_loaded = True
        return True

    def get_accounts(self) -> list[dict[str, Any]]:
        prefix = _settings().expected_account_prefix()
        return [
            {
                "account_no": f"{prefix}123456789",
                "account_kind": "01",
                "name": "주식",
                "trade_env": _settings().CREON_TRADE_ENV,
            }
        ]

    def submit_order(self, req: OrderSubmitRequest) -> OrderSubmitResponse:
        self.ensure_connected()
        self._rate_limiter.acquire()

        quote = self.get_quote(req.code)
        fill_price = req.price or quote.price
        self._order_seq += 1
        bono = str(self._order_seq)

        if req.side == "BUY":
            cost = fill_price * req.qty
            if cost > self._cash:
                self.last_error = "잔고부족"
                return OrderSubmitResponse(
                    accepted=False, raw_code=-307, raw_msg="잔고부족"
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
                    code=req.code,
                    qty=req.qty,
                    avg_price=fill_price,
                    eval_pnl=0.0,
                )
        else:  # SELL
            pos = self._positions.get(req.code)
            if not pos or pos.qty < req.qty:
                self.last_error = "매도수량부족"
                return OrderSubmitResponse(
                    accepted=False, raw_code=-308, raw_msg="매도수량부족"
                )
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
            trade_env=_settings().CREON_TRADE_ENV,
        )
        return OrderSubmitResponse(
            accepted=True, broker_order_no=bono, raw_code=0, raw_msg="정상"
        )

    def cancel_order(self, req: CancelRequest) -> OrderSubmitResponse:
        self._rate_limiter.acquire()
        log.info("mock_order_canceled", broker_order_no=req.broker_order_no)
        return OrderSubmitResponse(accepted=True, raw_code=0, raw_msg="취소완료")

    def get_balance(self) -> Balance:
        equity = sum(p.qty * p.avg_price for p in self._positions.values())
        return Balance(
            cash=self._cash, equity=equity, eval_amount=self._cash + equity
        )

    def get_positions(self) -> list[PositionItem]:
        return list(self._positions.values())

    def get_quote(self, code: str) -> Quote:
        base = 50000 + (hash(code) % 50000)
        price = float(base + random.randint(-200, 200))
        return Quote(
            code=code, price=price, change=0, change_pct=0, volume=1_000_000
        )

    def get_stock_master(self, code: str) -> StockMaster:
        # 종목별 결정성 있는 mock
        name_map = {
            "005930": ("삼성전자", "KOSPI", "반도체"),
            "000660": ("SK하이닉스", "KOSPI", "반도체"),
            "035420": ("NAVER", "KOSPI", "서비스업"),
        }
        name, market, sector = name_map.get(code, (f"종목{code}", "KOSPI", ""))
        price = self.get_quote(code).price
        return StockMaster(
            code=code,
            name=name,
            market=market,
            sector=sector,
            upper_limit=price * 1.3,
            lower_limit=price * 0.7,
        )

    def subscribe_realtime(
        self,
        codes: list[str],
        callback: Callable[[Quote], None] | None = None,
    ) -> int:
        if callback:
            for c in codes:
                self._tick_callbacks.setdefault(c, []).append(callback)
        log.info("mock_subscribed", count=len(codes))
        return len(codes)

    def unsubscribe_realtime(self, codes: list[str]) -> int:
        for c in codes:
            self._tick_callbacks.pop(c, None)
        return len(codes)

    def subscribe_orderbook(
        self,
        codes: list[str],
        callback: Callable[[OrderbookSnapshot], None] | None = None,
    ) -> int:
        if callback:
            for c in codes:
                self._orderbook_callbacks.setdefault(c, []).append(callback)
        log.info("mock_orderbook_subscribed", count=len(codes))
        return len(codes)

    def unsubscribe_orderbook(self, codes: list[str]) -> int:
        for c in codes:
            self._orderbook_callbacks.pop(c, None)
        return len(codes)

    def get_orderbook(self, code: str) -> OrderbookSnapshot:
        """결정성 있는 mock 호가 스냅샷 생성.

        - 기준가는 `get_quote(code)`의 price
        - 호가 단위는 가격대 따라 1~1000원 (KRX 호가 단위 단순화)
        - 잔량은 종목코드+단계로 deterministic
        """
        base = self.get_quote(code).price
        tick = _calc_tick_size(base)
        seed = (hash(code) % 1000) + 1
        bids: list[tuple[float, int]] = []
        asks: list[tuple[float, int]] = []
        for i in range(10):
            bid_price = max(1.0, round(base - tick * (i + 1)))
            ask_price = round(base + tick * (i + 1))
            # 1단계 가까운 호가일수록 잔량이 큰 경향
            bid_qty = (seed * (11 - i)) * 7 % 99999 + 10
            ask_qty = (seed * (11 - i)) * 11 % 99999 + 10
            bids.append((bid_price, bid_qty))
            asks.append((ask_price, ask_qty))
        total_bid = sum(q for _, q in bids)
        total_ask = sum(q for _, q in asks)
        return OrderbookSnapshot(
            code=code,
            bids=bids,
            asks=asks,
            total_bid_qty=total_bid,
            total_ask_qty=total_ask,
        )


# ---------------------------------------------------------------------------
# 실제 COM 어댑터 (Windows + pywin32)
# ---------------------------------------------------------------------------
class RealCreonAdapter(CreonAdapter):
    """CREON COM 객체를 통해 실제 주문을 수행. Windows 전용."""

    def __init__(self) -> None:
        super().__init__()
        self._win32: Any = None
        self._pythoncom: Any = None

        # lazy import (Linux/Mac 환경에서 모듈 import 자체는 가능)
        try:
            import pythoncom  # type: ignore[import-not-found]
            import win32com.client  # type: ignore[import-not-found]
            pythoncom.CoInitialize()
            self._pythoncom = pythoncom
            self._win32 = win32com.client
        except Exception as e:
            log.error("pywin32_unavailable", error=str(e))
            raise

        self.ensure_connected()
        if self.connected:
            self.initialize_trade()

    # ---------------- 연결 ----------------
    def ensure_connected(self) -> None:
        """`CpUtil.CpCybos.IsConnect`로 세션 확인. 미연결 시 자동 재시도."""
        try:
            cybos = self._win32.Dispatch("CpUtil.CpCybos")  # type: ignore[union-attr]
            self.connected = bool(cybos.IsConnect == 1)
            self.last_check_at = time.time()
            if not self.connected:
                self.last_error = "CREON 미연결 (CpCybos.IsConnect==0)"
        except Exception as e:
            log.exception("creon_ensure_connected_failed")
            self.connected = False
            self.account_loaded = False
            self.last_error = f"CpCybos dispatch 실패: {e}"

    def initialize_trade(self) -> bool:
        """`CpTrade.CpTdUtil.TradeInit()` 호출 + 비밀번호 검증 결과 처리.

        반환값:
        - True: 초기화 성공
        - False: 실패. self.last_error에 사유 기록
        """
        try:
            trade_util = self._win32.Dispatch("CpTrade.CpTdUtil")  # type: ignore[union-attr]
            ret = trade_util.TradeInit(0)
            if ret == 0:
                self.account_loaded = True
                log.info("creon_trade_init_ok")
                return True
            self.account_loaded = False
            self.last_error = f"TradeInit 실패 (코드={ret})"
            log.error("creon_trade_init_failed", code=ret)
            return False
        except Exception as e:
            self.account_loaded = False
            self.last_error = f"TradeInit 예외: {e}"
            log.exception("creon_trade_init_exception")
            return False

    def get_accounts(self) -> list[dict[str, Any]]:
        """전체 계좌를 조회 후 현재 모드(SIM/REAL)에 맞는 접두사만 필터링."""
        try:
            trade_util = self._win32.Dispatch("CpTrade.CpTdUtil")  # type: ignore[union-attr]
            count = trade_util.AccountNumber  # 배열 속성
            # CREON COM에서는 AccountNumber가 SafeArray로 반환됨
            accounts_raw = trade_util.AccountNumber  # type: ignore[assignment]
            # Windows COM은 튜플로 반환. 길이는 GetAccountType 등으로 별도 처리.
            account_list: list[dict[str, Any]] = []
            try:
                # PyWin32에서 AccountNumber는 sequence (튜플/리스트)
                for idx, acc_no in enumerate(accounts_raw):
                    kinds = trade_util.GoodsList(acc_no, 1)  # 1: 주식
                    kind = kinds[0] if kinds else "01"
                    account_list.append(
                        {
                            "account_no": str(acc_no),
                            "account_kind": str(kind),
                            "name": "주식",
                        }
                    )
            except TypeError:
                # 단일 값으로 반환되는 일부 환경 대응
                account_list.append(
                    {
                        "account_no": str(accounts_raw),
                        "account_kind": "01",
                        "name": "주식",
                    }
                )

            prefix = _settings().expected_account_prefix()
            filtered = [
                {**a, "trade_env": _settings().CREON_TRADE_ENV}
                for a in account_list
                if a["account_no"].startswith(prefix)
            ]
            log.info(
                "creon_accounts_loaded",
                total=len(account_list),
                filtered=len(filtered),
                trade_env=_settings().CREON_TRADE_ENV,
            )
            return filtered
        except Exception as e:
            log.exception("creon_get_accounts_failed")
            self.last_error = f"계좌 조회 실패: {e}"
            return []

    # ---------------- 주문 ----------------
    def submit_order(self, req: OrderSubmitRequest) -> OrderSubmitResponse:
        self.ensure_connected()
        if not self.connected:
            return OrderSubmitResponse(
                accepted=False, raw_code=-101, raw_msg="COM 미연결"
            )

        self._rate_limiter.acquire()

        try:
            obj = self._win32.Dispatch("CpTrade.CpTd0311")  # type: ignore[union-attr]
            obj.SetInputValue(0, "2" if req.side == "BUY" else "1")  # 1:매도 2:매수
            obj.SetInputValue(1, req.account_no or _settings().CREON_ACCOUNT_NO)
            obj.SetInputValue(2, req.account_kind or _settings().CREON_ACCOUNT_KIND)
            obj.SetInputValue(3, req.code)
            obj.SetInputValue(4, int(req.qty))
            obj.SetInputValue(5, int(req.price or 0))
            obj.SetInputValue(7, "0")  # 조건 (없음)
            obj.SetInputValue(8, "01" if req.order_type == "LIMIT" else "03")
            # 01: 보통, 03: 시장가

            ret = obj.BlockRequest()
            if ret != 0:
                raw_code = obj.GetDibStatus()
                raw_msg = obj.GetDibMsg1()
                self.last_error = f"주문 거부: {raw_msg}"
                return OrderSubmitResponse(
                    accepted=False, raw_code=raw_code, raw_msg=raw_msg
                )
            return OrderSubmitResponse(
                accepted=True,
                broker_order_no=str(obj.GetHeaderValue(8)),
                raw_code=0,
                raw_msg="정상",
            )
        except Exception as e:
            self.last_error = f"주문 예외: {e}"
            log.exception("creon_submit_failed")
            return OrderSubmitResponse(accepted=False, raw_code=-99, raw_msg=str(e))

    def cancel_order(self, req: CancelRequest) -> OrderSubmitResponse:
        self.ensure_connected()
        self._rate_limiter.acquire()
        try:
            obj = self._win32.Dispatch("CpTrade.CpTd0314")  # type: ignore[union-attr]
            obj.SetInputValue(1, req.broker_order_no)
            obj.SetInputValue(2, _settings().CREON_ACCOUNT_NO)
            obj.SetInputValue(3, _settings().CREON_ACCOUNT_KIND)
            obj.SetInputValue(4, req.code)
            obj.SetInputValue(5, int(req.qty or 0))

            ret = obj.BlockRequest()
            if ret != 0:
                self.last_error = f"취소 실패 코드={ret}"
                return OrderSubmitResponse(
                    accepted=False, raw_code=ret, raw_msg="취소 실패"
                )
            return OrderSubmitResponse(accepted=True, raw_code=0, raw_msg="취소완료")
        except Exception as e:
            self.last_error = f"취소 예외: {e}"
            log.exception("creon_cancel_failed")
            return OrderSubmitResponse(accepted=False, raw_code=-99, raw_msg=str(e))

    # ---------------- 잔고 ----------------
    def get_balance(self) -> Balance:
        """CpTrade.CpTd6033 호출. 종목 리스트 + 평가금액 집계."""
        self.ensure_connected()
        self._rate_limiter.acquire()
        try:
            obj = self._win32.Dispatch("CpTrade.CpTd6033")  # type: ignore[union-attr]
            obj.SetInputValue(0, _settings().CREON_ACCOUNT_NO)
            obj.SetInputValue(1, _settings().CREON_ACCOUNT_KIND)
            obj.SetInputValue(2, 50)  # 요청 건수
            ret = obj.BlockRequest()
            if ret != 0:
                self.last_error = f"잔고 조회 실패 코드={ret}"
                return Balance(cash=0.0, equity=0.0, eval_amount=0.0)

            # 헤더 9: 추정예수금, 10: 추정자산, 11: 평가금액 (CREON 명세 기준)
            cash = float(obj.GetHeaderValue(9))
            eval_amount = float(obj.GetHeaderValue(10))
            equity = eval_amount - cash
            return Balance(cash=cash, equity=equity, eval_amount=eval_amount)
        except Exception as e:
            self.last_error = f"잔고 예외: {e}"
            log.exception("creon_balance_failed")
            return Balance(cash=0.0, equity=0.0, eval_amount=0.0)

    def get_positions(self) -> list[PositionItem]:
        self.ensure_connected()
        self._rate_limiter.acquire()
        try:
            obj = self._win32.Dispatch("CpTrade.CpTd6033")  # type: ignore[union-attr]
            obj.SetInputValue(0, _settings().CREON_ACCOUNT_NO)
            obj.SetInputValue(1, _settings().CREON_ACCOUNT_KIND)
            obj.SetInputValue(2, 50)
            ret = obj.BlockRequest()
            if ret != 0:
                return []

            count = obj.GetHeaderValue(7)  # 종목 수
            positions: list[PositionItem] = []
            for i in range(count):
                positions.append(
                    PositionItem(
                        code=str(obj.GetDataValue(12, i)),  # 종목코드
                        qty=int(obj.GetDataValue(7, i)),    # 잔고수량
                        avg_price=float(obj.GetDataValue(17, i)),  # 평균단가
                        eval_pnl=float(obj.GetDataValue(11, i)),   # 평가손익
                    )
                )
            return positions
        except Exception as e:
            self.last_error = f"포지션 예외: {e}"
            log.exception("creon_positions_failed")
            return []

    # ---------------- 시세 ----------------
    def get_quote(self, code: str) -> Quote:
        self.ensure_connected()
        self._rate_limiter.acquire()
        try:
            obj = self._win32.Dispatch("Dscbo1.StockMst")  # type: ignore[union-attr]
            obj.SetInputValue(0, code)
            ret = obj.BlockRequest()
            if ret != 0:
                self.last_error = f"시세 실패 코드={ret}"
                return Quote(code=code, price=0.0)
            price = float(obj.GetHeaderValue(11))
            change = float(obj.GetHeaderValue(12))
            volume = int(obj.GetHeaderValue(18))
            return Quote(code=code, price=price, change=change, volume=volume)
        except Exception:
            log.exception("creon_quote_failed", code=code)
            return Quote(code=code, price=0.0)

    def get_stock_master(self, code: str) -> StockMaster:
        self.ensure_connected()
        self._rate_limiter.acquire()
        try:
            mgr = self._win32.Dispatch("CpUtil.CpCodeMgr")  # type: ignore[union-attr]
            name = str(mgr.CodeToName(code) or "")
            market_kind = int(mgr.GetStockMarketKind(code))  # 1:KOSPI 2:KOSDAQ
            market = "KOSPI" if market_kind == 1 else "KOSDAQ"
            sector_code = mgr.GetStockSectionKind(code)
            upper = float(mgr.GetStockMaxPrice(code))
            lower = float(mgr.GetStockMinPrice(code))
            status = int(mgr.GetStockStatusKind(code))  # 0:정상 1:거래정지 ...
            return StockMaster(
                code=code,
                name=name,
                market=market,
                sector=str(sector_code),
                is_suspended=(status != 0),
                upper_limit=upper,
                lower_limit=lower,
            )
        except Exception as e:
            self.last_error = f"종목마스터 예외: {e}"
            log.exception("creon_stock_master_failed")
            return StockMaster(code=code, name="", market="UNKNOWN")

    def subscribe_realtime(
        self,
        codes: list[str],
        callback: Callable[[Quote], None] | None = None,
    ) -> int:
        """`Dscbo1.StockCur` 구독 (종목별 인스턴스 1개)."""
        cnt = 0
        for c in codes:
            try:
                obj = self._win32.Dispatch("Dscbo1.StockCur")  # type: ignore[union-attr]
                obj.SetInputValue(0, c)
                # 콜백은 외부 워커가 처리; 여기서는 구독 등록만
                obj.Subscribe()
                if callback:
                    self._tick_callbacks.setdefault(c, []).append(callback)
                cnt += 1
            except Exception:
                log.exception("creon_subscribe_failed", code=c)
        return cnt

    def unsubscribe_realtime(self, codes: list[str]) -> int:
        cnt = 0
        for c in codes:
            try:
                obj = self._win32.Dispatch("Dscbo1.StockCur")  # type: ignore[union-attr]
                obj.SetInputValue(0, c)
                obj.Unsubscribe()
                self._tick_callbacks.pop(c, None)
                cnt += 1
            except Exception:
                log.exception("creon_unsubscribe_failed", code=c)
        return cnt

    # ---------------- 호가 (StockJpBid) ----------------
    def get_orderbook(self, code: str) -> OrderbookSnapshot:
        """`Dscbo1.StockJpBid` BlockRequest로 매수/매도 10단계 호가 조회.

        CREON `StockJpBid` 명세:
        - GetHeaderValue: 0=코드, 1=시간(HHMMSS)
        - GetDataValue(i, n): 매수 1~10 (n=0..9)
            * 0: 매도호가 가격
            * 1: 매수호가 가격
            * 2: 매도호가 잔량
            * 3: 매수호가 잔량
        실제 인덱스는 환경마다 차이가 있으므로 RealAdapter에서는 try/except 후 mock fallback.
        """
        self.ensure_connected()
        self._rate_limiter.acquire()
        try:
            obj = self._win32.Dispatch("Dscbo1.StockJpBid")  # type: ignore[union-attr]
            obj.SetInputValue(0, code)
            ret = obj.BlockRequest()
            if ret != 0:
                raise RuntimeError(f"StockJpBid BlockRequest 실패 코드={ret}")
            bids: list[tuple[float, int]] = []
            asks: list[tuple[float, int]] = []
            for i in range(10):
                ask_price = float(obj.GetDataValue(0, i))
                bid_price = float(obj.GetDataValue(1, i))
                ask_qty = int(obj.GetDataValue(2, i))
                bid_qty = int(obj.GetDataValue(3, i))
                asks.append((ask_price, ask_qty))
                bids.append((bid_price, bid_qty))
            return OrderbookSnapshot(
                code=code,
                bids=bids,
                asks=asks,
                total_bid_qty=sum(q for _, q in bids),
                total_ask_qty=sum(q for _, q in asks),
            )
        except Exception as e:
            self.last_error = f"호가 조회 예외: {e}"
            log.exception("creon_orderbook_failed", code=code)
            return OrderbookSnapshot(
                code=code, bids=[], asks=[], total_bid_qty=0, total_ask_qty=0
            )

    def subscribe_orderbook(
        self,
        codes: list[str],
        callback: Callable[[OrderbookSnapshot], None] | None = None,
    ) -> int:
        """`Dscbo1.StockJpBid` 실시간 호가 구독 (종목별 인스턴스 1개)."""
        cnt = 0
        for c in codes:
            try:
                obj = self._win32.Dispatch("Dscbo1.StockJpBid")  # type: ignore[union-attr]
                obj.SetInputValue(0, c)
                obj.Subscribe()
                if callback:
                    self._orderbook_callbacks.setdefault(c, []).append(callback)
                cnt += 1
            except Exception:
                log.exception("creon_orderbook_subscribe_failed", code=c)
        return cnt

    def unsubscribe_orderbook(self, codes: list[str]) -> int:
        cnt = 0
        for c in codes:
            try:
                obj = self._win32.Dispatch("Dscbo1.StockJpBid")  # type: ignore[union-attr]
                obj.SetInputValue(0, c)
                obj.Unsubscribe()
                self._orderbook_callbacks.pop(c, None)
                cnt += 1
            except Exception:
                log.exception("creon_orderbook_unsubscribe_failed", code=c)
        return cnt


# ---------------------------------------------------------------------------
# 팩토리
# ---------------------------------------------------------------------------
_adapter: CreonAdapter | None = None


def get_adapter() -> CreonAdapter:
    """싱글톤 어댑터.

    선택 규칙:
    1. CREON_FORCE_MOCK=true → 무조건 mock
    2. CREON_USE_MOCK=true 이고 Windows 아님 → mock
    3. Windows + pywin32 사용 가능 → Real
    4. 그 외 → mock (실패 시 fallback)
    """
    global _adapter
    if _adapter is not None:
        return _adapter

    if _settings().CREON_FORCE_MOCK:
        _adapter = MockCreonAdapter()
        log.info("creon_adapter_force_mock")
        return _adapter

    if not is_windows():
        _adapter = MockCreonAdapter()
        log.info("creon_adapter_non_windows_mock")
        return _adapter

    if _settings().CREON_USE_MOCK:
        _adapter = MockCreonAdapter()
        log.info("creon_adapter_use_mock_true")
        return _adapter

    try:
        _adapter = RealCreonAdapter()
        log.info(
            "creon_adapter_real_initialized",
            trade_env=_settings().CREON_TRADE_ENV,
        )
    except Exception as e:
        log.warning("creon_adapter_fallback_to_mock", error=str(e))
        _adapter = MockCreonAdapter()
    return _adapter


def reset_adapter() -> None:
    """테스트용: 싱글톤 리셋."""
    global _adapter
    _adapter = None
