"""백테스트 엔진 설정/입출력 데이터클래스.

- BacktestConfig: 엔진 진입점 입력
- BacktestResult: 엔진 산출 결과 (서비스 레이어가 DB 저장 시 가공)

한국 시장 관습 기본값:
- 수수료: 0.015% (대신증권 기준, 매수/매도 동일)
- 슬리피지: 0.05% (시장가 가정)
- 세금: 0.23% (코스피 매도 시. 코스닥/ETF는 다름)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


# ------------------------------------------------------------------
# 한국 시장 기본 상수
# ------------------------------------------------------------------
DEFAULT_FEE_RATE = Decimal("0.00015")       # 0.015%
DEFAULT_SLIPPAGE = Decimal("0.0005")        # 0.05%
DEFAULT_SELL_TAX = Decimal("0.0023")        # 0.23% (KOSPI)
DEFAULT_KOSDAQ_TAX = Decimal("0.0018")      # 0.18% (KOSDAQ)


@dataclass
class BacktestConfig:
    """백테스트 입력.

    Attributes:
        universe: 종목 코드 리스트 (예: ["005930", "000660"])
        strategy_type: 전략 식별자. registry에 등록된 키 (예: "golden_cross") 또는
            "composite" 지정 시 strategy_id 의 strategy_rules 를 사용.
        strategy_id: composite 전략 사용 시 DB의 strategies.id
        period_from: 백테스트 시작일
        period_to: 백테스트 종료일
        initial_capital: 초기자본 (원)
        fee_rate: 수수료율 (대칭, 매수/매도 동일)
        slippage: 슬리피지 비율
        sell_tax: 매도 시 세금 (KOSPI 기준 0.23%)
        max_positions: 동시 보유 가능한 최대 포지션 수
        position_sizing: 'equal'(균등분할) | 'fixed_pct'(고정 비율)
        position_pct: position_sizing=fixed_pct 일 때 1포지션 자본 비율 (0~1)
        execution_lag: 'close'(당일 종가 체결) | 'next_open'(익일 시가 체결)
        strategy_params: 전략별 파라미터 (단순 키-값)
    """

    universe: list[str]
    strategy_type: str
    period_from: date
    period_to: date
    initial_capital: Decimal
    strategy_id: int | None = None
    fee_rate: Decimal = DEFAULT_FEE_RATE
    slippage: Decimal = DEFAULT_SLIPPAGE
    sell_tax: Decimal = DEFAULT_SELL_TAX
    max_positions: int = 5
    position_sizing: str = "equal"
    position_pct: Decimal = Decimal("0.2")
    execution_lag: str = "close"
    strategy_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeRecord:
    """엔진 내부 거래 표현 (DB 저장 전 단계)."""

    code: str
    side: str                       # BUY / SELL
    entry_price: Decimal
    exit_price: Decimal | None
    qty: int
    pnl: Decimal | None
    entry_at: date
    exit_at: date | None
    fee: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")


@dataclass
class BacktestResult:
    """엔진 산출 결과 (서비스가 ORM 매핑)."""

    metrics: dict[str, Any]                   # cumulative_return, mdd, sharpe ...
    equity_curve: list[dict[str, Any]]        # [{date, equity, drawdown, cash}]
    trades: list[TradeRecord]                 # 개별 거래 내역
    monthly_returns: dict[str, float]         # {"2026-01": 0.034, ...}
    summary: dict[str, Any]                   # 엔진 메타 (engine name, version, params 등)
