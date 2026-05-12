"""시그널 → 주문 변환 엔진.

설계 개요:
1) 시그널은 종목별 pd.Series (1=매수, -1=매도, 0=홀드) 형태로 사전 산출된다.
2) 거래일을 순회하며(event-driven) 각 종목 시그널을 처리한다.
3) 매수:
   - 보유 중이면 무시 (피라미딩 미지원)
   - 최대 포지션 수 도달 시 무시
   - 포지션 사이징: equal(가용 자본 / 잔여 슬롯) 또는 fixed_pct(초기자본 * pct)
   - 1주 미만은 매수 불가
4) 매도:
   - 보유 중일 때만 전량 청산
5) 매 거래일 종료 시 mark-to-market → equity_curve 기록

체결 옵션:
- config.execution_lag = 'close': 시그널 발생일의 종가에 체결 (시그널을 사전 shift 했으므로 룩어헤드 아님)
- config.execution_lag = 'next_open': 다음 거래일 시가에 체결 (더 보수적)
"""
from __future__ import annotations

from datetime import date
from typing import Callable

import pandas as pd
import structlog

from app.services.backtest_engine.config import BacktestConfig
from app.services.backtest_engine.portfolio import Portfolio

log = structlog.get_logger(__name__)


class BacktestExecutor:
    """이벤트 드리븐 실행기."""

    def __init__(
        self,
        config: BacktestConfig,
        frames: dict[str, pd.DataFrame],
        signals: dict[str, pd.Series],
        progress_cb: Callable[[int], None] | None = None,
    ) -> None:
        self.config = config
        self.frames = frames
        self.signals = signals
        self.progress_cb = progress_cb

        self.portfolio = Portfolio(
            initial_cash=float(config.initial_capital),
            fee_rate=float(config.fee_rate),
            slippage=float(config.slippage),
            sell_tax=float(config.sell_tax),
        )

        # 공통 거래일 인덱스 (모든 종목 합집합 후 정렬)
        all_dates: set[pd.Timestamp] = set()
        for df in frames.values():
            all_dates.update(df.index.tolist())
        self.calendar: list[pd.Timestamp] = sorted(all_dates)

    # ------------------------------------------------------------------
    def run(self) -> list[dict[str, float | str]]:
        """전체 백테스트 실행.

        Returns:
            equity_curve: [{date, equity, drawdown, cash}, ...]
        """
        equity_curve: list[dict[str, float | str]] = []
        peak_equity = float(self.config.initial_capital)
        total_days = len(self.calendar) or 1

        for i, ts in enumerate(self.calendar):
            day: date = ts.date() if hasattr(ts, "date") else ts  # type: ignore[assignment]

            # 1) 매도 처리 우선 (현금 확보 후 매수)
            for code in list(self.portfolio.positions.keys()):
                pos = self.portfolio.positions[code]
                if pos.qty <= 0:
                    continue
                sig = self._signal_at(code, ts)
                if sig == -1:
                    px = self._execute_price(code, ts)
                    if px is not None:
                        self.portfolio.sell(day, code, px, pos.qty)

            # 2) 매수 처리
            for code in self.frames.keys():
                if self.portfolio.has_position(code):
                    continue
                if self.portfolio.open_position_count() >= self.config.max_positions:
                    break
                sig = self._signal_at(code, ts)
                if sig != 1:
                    continue
                px = self._execute_price(code, ts)
                if px is None or px <= 0:
                    continue
                qty = self._size_position(px)
                if qty > 0:
                    self.portfolio.buy(day, code, px, qty)

            # 3) Mark-to-market
            prices_today = self._prices_at(ts)
            equity = self.portfolio.mark_to_market(prices_today)
            peak_equity = max(peak_equity, equity)
            drawdown = (equity / peak_equity - 1.0) if peak_equity > 0 else 0.0

            equity_curve.append(
                {
                    "date": day.isoformat(),
                    "equity": round(equity, 2),
                    "drawdown": round(drawdown, 6),
                    "cash": round(self.portfolio.cash, 2),
                }
            )

            # 진행률 콜백 (시뮬레이션 페이즈: 30 → 80 사이)
            if self.progress_cb and (i % max(1, total_days // 50) == 0):
                pct = 30 + int(50 * (i + 1) / total_days)
                self.progress_cb(min(pct, 80))

        return equity_curve

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _signal_at(self, code: str, ts: pd.Timestamp) -> int:
        sig_series = self.signals.get(code)
        if sig_series is None or ts not in sig_series.index:
            return 0
        try:
            return int(sig_series.loc[ts])
        except (KeyError, ValueError):
            return 0

    def _execute_price(self, code: str, ts: pd.Timestamp) -> float | None:
        df = self.frames.get(code)
        if df is None or ts not in df.index:
            return None
        if self.config.execution_lag == "next_open":
            idx = df.index.get_loc(ts)
            if isinstance(idx, slice) or idx + 1 >= len(df.index):
                return None
            return float(df.iloc[idx + 1]["open"])
        return float(df.loc[ts, "close"])

    def _prices_at(self, ts: pd.Timestamp) -> dict[str, float]:
        out: dict[str, float] = {}
        for code, df in self.frames.items():
            if ts in df.index:
                out[code] = float(df.loc[ts, "close"])
        return out

    def _size_position(self, price: float) -> int:
        """포지션 크기 산정.

        equal: 가용 현금을 (최대포지션 - 보유포지션) 으로 나눈다.
        fixed_pct: 초기자본 * position_pct.
        """
        slots_left = max(1, self.config.max_positions - self.portfolio.open_position_count())
        if self.config.position_sizing == "fixed_pct":
            budget = float(self.config.initial_capital) * float(self.config.position_pct)
        else:
            budget = self.portfolio.cash / slots_left
        # 수수료 + 슬리피지 여유분 1.5% 보수적 차감
        budget *= 0.985
        qty = int(budget // price)
        return max(qty, 0)
