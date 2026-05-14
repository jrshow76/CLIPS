"""익스포트 종류별 데이터 추출기.

각 추출기는 ``async def extract(db, user_id, filter_params) -> dict[str, pd.DataFrame]``
시그니처를 따른다. 반환값은 시트명 → DataFrame 매핑이며 CSV 단일 시트인 경우에도
첫 번째 항목을 메인 시트로 사용한다.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Mapping

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.export_engine.extractors.backtest_extractor import extract_backtest
from app.services.export_engine.extractors.orders_extractor import extract_orders
from app.services.export_engine.extractors.pnl_extractor import extract_pnl
from app.services.export_engine.extractors.positions_extractor import extract_positions
from app.services.export_engine.extractors.signals_extractor import extract_signals

Extractor = Callable[
    [AsyncSession, int, Mapping[str, Any]],
    Awaitable[dict[str, pd.DataFrame]],
]

# 익스포트 종류 → 추출기 매핑
EXTRACTORS: Mapping[str, Extractor] = {
    "ORDERS": extract_orders,
    "PNL": extract_pnl,
    "BACKTEST": extract_backtest,
    "SIGNALS": extract_signals,
    "POSITIONS": extract_positions,
}

__all__ = ["EXTRACTORS", "Extractor"]
