"""KIS 계좌/잔고/체결내역 어댑터.

KIS 응답을 본체 도메인 표준 dict 로 변환한다.
- ``get_balance()``: {cash, equity, eval_amount, positions[]}
- ``get_positions()``: 보유 종목 리스트
- ``get_recent_fills(from_date, to_date)``: 일별 체결 내역
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

import structlog

from app.integrations.kis.client import KisClient, get_kis_client

log = structlog.get_logger(__name__)


@dataclass
class KisBalance:
    """KIS 잔고 표준화."""

    cash: float
    equity: float
    eval_amount: float
    positions: list[dict[str, Any]]


def _f(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except Exception:  # noqa: BLE001
        return default


class KisAccountAdapter:
    """KIS 계좌 정보 어댑터."""

    def __init__(self, client: KisClient | None = None) -> None:
        self._client = client or get_kis_client()

    async def get_balance(self) -> KisBalance:
        resp = await self._client.get_balance()
        # output1: 종목별 보유, output2[0]: 계좌 평가 요약
        out1 = resp.get("output1") or []
        out2 = resp.get("output2") or [{}]
        summary = out2[0] if out2 else {}

        positions = [
            {
                "code": str(p.get("pdno", "")).zfill(6),
                "qty": int(_f(p.get("hldg_qty"))),
                "avg_price": _f(p.get("pchs_avg_pric")),
                "eval_pnl": _f(p.get("evlu_pfls_amt")),
                "eval_price": _f(p.get("prpr")),
            }
            for p in out1
            if int(_f(p.get("hldg_qty"))) > 0
        ]
        cash = _f(summary.get("dnca_tot_amt"))  # 예수금 총금액
        eval_amount = _f(summary.get("tot_evlu_amt"))  # 총평가
        equity = max(0.0, eval_amount - cash)
        return KisBalance(
            cash=cash, equity=equity, eval_amount=eval_amount, positions=positions
        )

    async def get_positions(self) -> list[dict[str, Any]]:
        b = await self.get_balance()
        return b.positions

    async def get_recent_fills(
        self, from_date: date, to_date: date
    ) -> list[dict[str, Any]]:
        """체결 내역 리스트."""
        resp = await self._client.get_order_history(
            from_date=from_date.strftime("%Y%m%d"),
            to_date=to_date.strftime("%Y%m%d"),
        )
        out = resp.get("output1") or []
        return [
            {
                "code": str(r.get("pdno", "")).zfill(6),
                "side": "BUY" if r.get("sll_buy_dvsn_cd") == "02" else "SELL",
                "qty": int(_f(r.get("tot_ccld_qty"))),
                "price": _f(r.get("avg_prvs")),
                "fill_amount": _f(r.get("tot_ccld_amt")),
                "ord_dt": r.get("ord_dt"),
                "broker_order_no": str(r.get("odno", "")),
            }
            for r in out
        ]

    @staticmethod
    def to_dict(balance: KisBalance) -> dict[str, Any]:
        return asdict(balance)
