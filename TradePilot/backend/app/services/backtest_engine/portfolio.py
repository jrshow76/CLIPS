"""백테스트 포트폴리오 (현금/포지션/거래내역 추적).

float 기반 (DB 저장 직전에 Decimal 변환). 1주 단위 정수 수량을 보장한다.

수수료 0.015%, 매도세 0.23% (KOSPI), 슬리피지 0.05% 가 기본.
실제 체결가 = price * (1 ± slippage).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.services.backtest_engine.config import TradeRecord
from app.services.backtest_engine.data_loader import to_decimal


@dataclass
class Position:
    """단일 종목 보유 포지션."""

    code: str
    qty: int = 0
    avg_price: float = 0.0
    opened_at: date | None = None


@dataclass
class Portfolio:
    """포트폴리오 시뮬레이터.

    Args:
        initial_cash: 시작 현금
        fee_rate: 수수료율 (매수/매도 대칭)
        slippage: 슬리피지 비율
        sell_tax: 매도세
    """

    initial_cash: float
    fee_rate: float = 0.00015
    slippage: float = 0.0005
    sell_tax: float = 0.0023

    cash: float = field(init=False)
    positions: dict[str, Position] = field(init=False, default_factory=dict)
    closed_trades: list[TradeRecord] = field(init=False, default_factory=list)
    # 미청산 매수: 청산 시 pnl 계산을 위해 entry 정보 보관
    _open_entries: dict[str, dict] = field(init=False, default_factory=dict)
    total_fee_paid: float = field(init=False, default=0.0)
    total_tax_paid: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        self.cash = float(self.initial_cash)

    # ------------------------------------------------------------------
    # 거래
    # ------------------------------------------------------------------
    def buy(self, ts: date, code: str, price: float, qty: int) -> bool:
        """시장가 매수. 자본 부족 시 False."""
        if qty <= 0 or price <= 0:
            return False

        # 슬리피지: 매수는 불리한 방향(상승)
        fill_price = price * (1.0 + self.slippage)
        gross = fill_price * qty
        fee = gross * self.fee_rate
        total_cost = gross + fee

        if total_cost > self.cash:
            # 자본 부족: 가능한 만큼으로 조정
            max_qty = int(self.cash // (fill_price * (1.0 + self.fee_rate)))
            if max_qty <= 0:
                return False
            qty = max_qty
            gross = fill_price * qty
            fee = gross * self.fee_rate
            total_cost = gross + fee

        self.cash -= total_cost
        self.total_fee_paid += fee

        pos = self.positions.get(code)
        if pos is None:
            pos = Position(code=code, opened_at=ts)
            self.positions[code] = pos

        new_total_qty = pos.qty + qty
        # 가중평균단가 (수수료 포함)
        pos.avg_price = (pos.avg_price * pos.qty + fill_price * qty) / new_total_qty if new_total_qty else 0.0
        pos.qty = new_total_qty
        if pos.opened_at is None:
            pos.opened_at = ts

        # 미청산 entry 트랙 (단순화: 종목별 1개 entry 묶음)
        self._open_entries[code] = {
            "entry_price": pos.avg_price,
            "entry_at": pos.opened_at or ts,
            "fee_accumulated": fee + self._open_entries.get(code, {}).get("fee_accumulated", 0.0),
        }
        return True

    def sell(self, ts: date, code: str, price: float, qty: int) -> bool:
        """시장가 매도. 보유량 초과는 보유량으로 클램프."""
        pos = self.positions.get(code)
        if pos is None or pos.qty <= 0 or qty <= 0 or price <= 0:
            return False

        qty = min(qty, pos.qty)
        # 슬리피지: 매도는 불리한 방향(하락)
        fill_price = price * (1.0 - self.slippage)
        gross = fill_price * qty
        fee = gross * self.fee_rate
        tax = gross * self.sell_tax
        proceeds = gross - fee - tax

        self.cash += proceeds
        self.total_fee_paid += fee
        self.total_tax_paid += tax

        # PnL: (체결가 - 평균매수가) * qty - 거래비용
        entry_info = self._open_entries.get(code, {})
        entry_price = entry_info.get("entry_price", pos.avg_price)
        entry_at = entry_info.get("entry_at", ts)
        pnl = (fill_price - entry_price) * qty - fee - tax - entry_info.get("fee_accumulated", 0.0) * (qty / pos.qty if pos.qty else 1.0)

        self.closed_trades.append(
            TradeRecord(
                code=code,
                side="SELL",
                entry_price=to_decimal(entry_price),
                exit_price=to_decimal(fill_price),
                qty=qty,
                pnl=to_decimal(pnl),
                entry_at=entry_at,
                exit_at=ts,
                fee=to_decimal(fee),
                tax=to_decimal(tax),
            )
        )

        pos.qty -= qty
        if pos.qty == 0:
            pos.avg_price = 0.0
            pos.opened_at = None
            self._open_entries.pop(code, None)
        return True

    # ------------------------------------------------------------------
    # 평가
    # ------------------------------------------------------------------
    def mark_to_market(self, prices: dict[str, float]) -> float:
        """현재 보유 포지션을 prices 로 평가한 총 자본을 반환."""
        equity = self.cash
        for code, pos in self.positions.items():
            if pos.qty == 0:
                continue
            px = prices.get(code, pos.avg_price)
            equity += px * pos.qty
        return equity

    def equity(self, prices: dict[str, float] | None = None) -> float:
        if prices is None:
            return self.cash + sum(p.qty * p.avg_price for p in self.positions.values())
        return self.mark_to_market(prices)

    def open_position_count(self) -> int:
        return sum(1 for p in self.positions.values() if p.qty > 0)

    def has_position(self, code: str) -> bool:
        pos = self.positions.get(code)
        return pos is not None and pos.qty > 0
