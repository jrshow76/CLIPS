"""영문 컬럼명 → 한글 표시명 매핑 + 컬럼별 포맷 분류.

모든 익스포트 시트에서 동일한 한글 표기를 보장한다.
새 컬럼 추가 시 본 매핑과 (포맷이 필요한 경우) 분류 집합에 함께 등록한다.
"""
from __future__ import annotations

from typing import Mapping

import pandas as pd


# ---------------------------------------------------------------------------
# 영문 컬럼 → 한글 헤더 매핑
# 누락된 컬럼은 원본 이름을 그대로 사용한다.
# ---------------------------------------------------------------------------
HEADER_MAP: Mapping[str, str] = {
    # 공통
    "id": "ID",
    "public_id": "공개ID",
    "user_id": "사용자ID",
    "created_at": "생성시각",
    "updated_at": "수정시각",
    "trade_date": "거래일자",
    # 종목/시장
    "code": "종목코드",
    "name": "종목명",
    "sector": "섹터",
    "market": "시장",
    # 주문
    "order_id": "주문번호",
    "side": "매매구분",
    "order_type": "주문유형",
    "trade_mode": "매매모드",
    "qty": "수량",
    "price": "주문가격",
    "status": "상태",
    "ordered_at": "주문시각",
    "filled_at": "체결시각",
    "canceled_at": "취소시각",
    "executed_at": "체결시각",
    "broker_order_no": "증권사주문번호",
    "reject_reason": "거부사유",
    # 체결
    "fill_qty": "체결수량",
    "fill_price": "체결가격",
    "fee": "수수료",
    "tax": "거래세",
    "slippage": "슬리피지",
    "amount": "거래금액",
    # 손익
    "realized_pnl": "실현손익",
    "unrealized_pnl": "평가손익",
    "total_pnl": "총손익",
    "pnl": "손익",
    "mdd": "최대낙폭",
    "win_count": "익절건수",
    "loss_count": "손절건수",
    "win_rate": "승률",
    "cumulative_return": "누적수익률",
    "annualized_return": "연환산수익률",
    "sharpe": "샤프지수",
    # 포지션
    "avg_price": "평균단가",
    "current_price": "현재가",
    "pnl_pct": "수익률",
    # 백테스트
    "run_id": "백테스트ID",
    "strategy_id": "전략ID",
    "strategy_name": "전략명",
    "entry_price": "진입가",
    "exit_price": "청산가",
    "entry_at": "진입시각",
    "exit_at": "청산시각",
    "trade_count": "거래건수",
    "initial_capital": "초기자본",
    "period_from": "기간시작",
    "period_to": "기간종료",
    # 시그널
    "signal_id": "시그널ID",
    "signal_type": "시그널유형",
    "indicator": "지표",
    "score": "점수",
    "triggered_at": "발생시각",
    # 포트폴리오
    "cash": "현금",
    "equity": "주식평가",
    "total_value": "총자산",
}


# ---------------------------------------------------------------------------
# 컬럼 카테고리 (XLSX 셀 포맷 결정에 사용)
# ---------------------------------------------------------------------------
NUMERIC_COLUMNS: frozenset[str] = frozenset(
    {
        "qty", "fill_qty", "win_count", "loss_count", "trade_count",
    }
)

CURRENCY_COLUMNS: frozenset[str] = frozenset(
    {
        "price", "fill_price", "fee", "tax", "amount",
        "realized_pnl", "unrealized_pnl", "total_pnl", "pnl",
        "avg_price", "current_price", "entry_price", "exit_price",
        "cash", "equity", "total_value", "initial_capital",
    }
)

PERCENT_COLUMNS: frozenset[str] = frozenset(
    {
        "mdd", "win_rate", "cumulative_return", "annualized_return",
        "pnl_pct", "slippage", "score",
    }
)

DATE_COLUMNS: frozenset[str] = frozenset(
    {"trade_date", "period_from", "period_to"}
)

DATETIME_COLUMNS: frozenset[str] = frozenset(
    {
        "created_at", "updated_at", "ordered_at", "filled_at",
        "canceled_at", "executed_at", "entry_at", "exit_at",
        "triggered_at",
    }
)


def translate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame 컬럼명을 한글로 치환한 사본을 반환한다.

    매핑에 없는 컬럼은 원본 이름을 유지한다. 원본 df 는 수정하지 않는다.
    """
    if df.empty:
        return df.rename(columns=lambda c: HEADER_MAP.get(str(c), str(c)))
    new_cols = {c: HEADER_MAP.get(str(c), str(c)) for c in df.columns}
    return df.rename(columns=new_cols)
