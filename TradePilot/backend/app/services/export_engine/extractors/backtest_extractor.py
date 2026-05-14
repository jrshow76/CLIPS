"""백테스트 결과 익스포트 추출기.

필터:
    * ``run_id`` - 특정 백테스트 잡 1건(우선)
    * ``run_id_list`` - 다수 잡 비교
    * 미지정 시 최근 10건

시트:
    * 백테스트 요약 - runs 헤더 + 메트릭
    * 거래내역 - backtest_trades 행
    * 자본곡선 - JSONB equity_curve 평탄화
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

import pandas as pd
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestResult, BacktestRun, BacktestTrade
from app.models.market import Stock
from app.models.trade import Strategy


async def extract_backtest(
    db: AsyncSession,
    user_id: int,
    filter_params: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    """백테스트 결과를 3 시트로 반환."""
    # 1. run 식별자 결정
    run_ids: list[int] = []
    if filter_params.get("run_id"):
        # public_id(UUID) 또는 정수 id 둘 다 허용
        ident = filter_params["run_id"]
        run = await _find_run(db, user_id, ident)
        if run is not None:
            run_ids = [run.id]
    elif filter_params.get("run_id_list"):
        for ident in filter_params["run_id_list"]:
            run = await _find_run(db, user_id, ident)
            if run is not None:
                run_ids.append(run.id)

    if not run_ids:
        # 최근 10건 fallback
        stmt = (
            select(BacktestRun.id)
            .where(BacktestRun.user_id == user_id)
            .order_by(BacktestRun.created_at.desc())
            .limit(10)
        )
        run_ids = [row[0] for row in (await db.execute(stmt)).all()]

    # 2. 요약 시트
    summary_rows: list[dict[str, Any]] = []
    if run_ids:
        stmt = (
            select(BacktestRun, BacktestResult, Strategy.name)
            .join(BacktestResult, BacktestResult.run_id == BacktestRun.id, isouter=True)
            .join(Strategy, Strategy.id == BacktestRun.strategy_id, isouter=True)
            .where(BacktestRun.id.in_(run_ids))
            .order_by(BacktestRun.created_at.desc())
        )
        for run, result, strategy_name in (await db.execute(stmt)).all():
            summary_rows.append(
                {
                    "run_id": str(run.job_id),
                    "strategy_name": strategy_name or "",
                    "period_from": run.period_from,
                    "period_to": run.period_to,
                    "initial_capital": _to_num(run.initial_capital),
                    "status": run.status,
                    "cumulative_return": _to_num(result.cumulative_return) if result else None,
                    "annualized_return": _to_num(result.annualized_return) if result else None,
                    "mdd": _to_num(result.mdd) if result else None,
                    "sharpe": _to_num(result.sharpe) if result else None,
                    "win_rate": _to_num(result.win_rate) if result else None,
                    "trade_count": result.trade_count if result else 0,
                }
            )
    summary_df = pd.DataFrame(
        summary_rows,
        columns=[
            "run_id", "strategy_name", "period_from", "period_to",
            "initial_capital", "status",
            "cumulative_return", "annualized_return", "mdd", "sharpe",
            "win_rate", "trade_count",
        ],
    )

    # 3. 거래내역 시트
    trade_rows: list[dict[str, Any]] = []
    if run_ids:
        stmt = (
            select(BacktestTrade, Stock.code, Stock.name)
            .join(Stock, Stock.id == BacktestTrade.stock_id, isouter=True)
            .where(BacktestTrade.run_id.in_(run_ids))
            .order_by(BacktestTrade.entry_at.asc())
        )
        for trade, code, name in (await db.execute(stmt)).all():
            trade_rows.append(
                {
                    "run_id": trade.run_id,
                    "code": code or "",
                    "name": name or "",
                    "side": trade.side,
                    "qty": _to_num(trade.qty),
                    "entry_price": _to_num(trade.entry_price),
                    "exit_price": _to_num(trade.exit_price),
                    "pnl": _to_num(trade.pnl),
                    "entry_at": trade.entry_at,
                    "exit_at": trade.exit_at,
                }
            )
    trades_df = pd.DataFrame(
        trade_rows,
        columns=[
            "run_id", "code", "name", "side", "qty",
            "entry_price", "exit_price", "pnl",
            "entry_at", "exit_at",
        ],
    )

    # 4. 자본곡선 시트 (JSONB → row 평탄화)
    curve_rows: list[dict[str, Any]] = []
    if run_ids:
        stmt = select(BacktestResult).where(BacktestResult.run_id.in_(run_ids))
        for result in (await db.execute(stmt)).scalars().all():
            ec = result.equity_curve
            if not ec:
                continue
            # 지원 포맷:
            #   1) {"points": [{"ts": "2025-01-01", "equity": 100}]}
            #   2) [{"ts": ..., "equity": ...}, ...]
            points = ec.get("points") if isinstance(ec, dict) else ec
            if not isinstance(points, list):
                continue
            for p in points:
                if not isinstance(p, dict):
                    continue
                curve_rows.append(
                    {
                        "run_id": result.run_id,
                        "trade_date": p.get("ts") or p.get("date"),
                        "equity": p.get("equity") or p.get("value"),
                    }
                )
    curve_df = pd.DataFrame(curve_rows, columns=["run_id", "trade_date", "equity"])

    return {"백테스트요약": summary_df, "거래내역": trades_df, "자본곡선": curve_df}


async def _find_run(db: AsyncSession, user_id: int, ident: Any) -> BacktestRun | None:
    """run 식별자(UUID 또는 int) 로 본인 잡 조회."""
    import uuid as _uuid

    # int 시도
    try:
        rid = int(ident)
        stmt = select(BacktestRun).where(
            and_(BacktestRun.id == rid, BacktestRun.user_id == user_id)
        )
        result = (await db.execute(stmt)).scalar_one_or_none()
        if result is not None:
            return result
    except (TypeError, ValueError):
        pass
    # UUID 시도
    try:
        uid = _uuid.UUID(str(ident))
        stmt = select(BacktestRun).where(
            and_(BacktestRun.job_id == uid, BacktestRun.user_id == user_id)
        )
        return (await db.execute(stmt)).scalar_one_or_none()
    except (TypeError, ValueError):
        return None


def _to_num(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v
