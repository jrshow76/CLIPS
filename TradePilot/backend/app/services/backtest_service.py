"""백테스트 서비스 (실 엔진 연동 버전).

기능:
- 잡 생성/입력검증/동시실행 제한
- Celery 워커 enqueue (워커 미가용 시 즉시 동기 실행 fallback)
- 잡 상태/결과/거래내역(페이지네이션)/취소/저장/비교
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.backtest import BacktestResult, BacktestRun, BacktestTrade
from app.models.market import Stock
from app.repositories.backtest_repository import (
    BacktestResultRepository,
    BacktestRunRepository,
    BacktestTradeRepository,
)
from app.repositories.stock_repository import StockExtRepository
from app.repositories.strategy_repository import StrategyRepository

log = structlog.get_logger(__name__)


# 입력 한도
MIN_PERIOD_DAYS = 30
MAX_PERIOD_DAYS = 365 * 5
MIN_CAPITAL = Decimal("1000000")          # 100만원 (DDL ck_bt_runs_capital 일치)
MAX_CAPITAL = Decimal("10000000000")      # 100억
MAX_CONCURRENT_RUNS_PER_USER = 3


class BacktestService:
    """백테스트 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.runs = BacktestRunRepository(db)
        self.results = BacktestResultRepository(db)
        self.trades = BacktestTradeRepository(db)
        self.strategies = StrategyRepository(db)
        self.stocks = StockExtRepository(db)

    # ------------------------------------------------------------------
    # 잡 큐잉
    # ------------------------------------------------------------------
    async def enqueue(
        self,
        *,
        user_id: int,
        strategy_public_id: str,
        universe: list[str],
        from_date: date,
        to_date: date,
        initial_capital: Decimal,
        slippage: Decimal,
        fee_rate: Decimal,
    ) -> BacktestRun:
        # 입력 검증
        errors: dict[str, list[str]] = {}
        period_days = (to_date - from_date).days
        if period_days < MIN_PERIOD_DAYS:
            errors["period"] = [f"최소 {MIN_PERIOD_DAYS}일 이상이어야 합니다."]
        elif period_days > MAX_PERIOD_DAYS:
            errors["period"] = [f"최대 {MAX_PERIOD_DAYS}일까지 허용됩니다."]
        if not (MIN_CAPITAL <= initial_capital <= MAX_CAPITAL):
            errors["initial_capital"] = ["허용 범위를 벗어났습니다."]
        if slippage < 0 or slippage > Decimal("0.1"):
            errors["slippage"] = ["0 ~ 0.1 사이여야 합니다."]
        if fee_rate < 0 or fee_rate > Decimal("0.01"):
            errors["fee_rate"] = ["0 ~ 0.01 사이여야 합니다."]
        if not universe:
            errors["universe"] = ["1개 이상의 종목코드가 필요합니다."]
        if errors:
            raise AppException("E0032", details=errors)

        strategy = await self.strategies.find_by_public_id(strategy_public_id)
        if not strategy or strategy.user_id != user_id:
            raise AppException("E0062", message="전략을 찾을 수 없습니다.")

        # 동시 실행 제한
        active = await self._count_active_runs(user_id)
        if active >= MAX_CONCURRENT_RUNS_PER_USER:
            raise AppException(
                "E0032",
                message=f"동시 실행 한도({MAX_CONCURRENT_RUNS_PER_USER}건)를 초과했습니다.",
                details={"active": [str(active)]},
            )

        run = BacktestRun(
            user_id=user_id,
            strategy_id=strategy.id,
            universe=universe,
            period_from=from_date,
            period_to=to_date,
            initial_capital=initial_capital,
            slippage=slippage,
            fee_rate=fee_rate,
            status="QUEUED",
            progress=0,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        # Celery 태스크 큐잉 (워커 미가용 시 동기 fallback)
        try:
            from app.workers.tasks.backtest_tasks import run_backtest as run_task

            run_task.delay(str(run.job_id))
        except Exception as e:
            log.warning("backtest_enqueue_celery_failed", error=str(e))
            # 동기 실행으로 fallback (시연/단위테스트 환경)
            await self._run_inline(run)

        log.info("backtest_enqueued", user_id=user_id, job_id=str(run.job_id))
        return run

    # ------------------------------------------------------------------
    # 조회/취소/저장
    # ------------------------------------------------------------------
    async def get_run(self, *, user_id: int, job_id: str) -> BacktestRun:
        run = await self.runs.find_by_job_id(job_id)
        if not run or run.user_id != user_id:
            raise AppException("E0062", message="백테스트 잡을 찾을 수 없습니다.")
        return run

    async def cancel(self, *, user_id: int, job_id: str) -> BacktestRun:
        run = await self.get_run(user_id=user_id, job_id=job_id)
        if run.status in ("DONE", "CANCELED", "FAILED"):
            raise AppException(
                "E0003",
                details={"status": [f"현재 상태({run.status})에서 취소할 수 없습니다."]},
            )
        # Celery 작업 취소 시도
        try:
            from app.workers.celery_app import celery_app

            celery_app.control.revoke(str(run.job_id), terminate=True)
        except Exception as e:
            log.warning("backtest_cancel_revoke_failed", error=str(e))

        run.status = "CANCELED"
        run.finished_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        return run

    async def get_result(self, *, user_id: int, job_id: str) -> dict[str, Any]:
        run = await self.get_run(user_id=user_id, job_id=job_id)
        if run.finished_at and run.finished_at < datetime.now(tz=timezone.utc) - timedelta(days=30):
            raise AppException("E0031", message="백테스트 결과가 만료되었습니다.")
        result = await self.db.get(BacktestResult, run.id)
        trades = await self.trades.list_for_run(run.id)
        # stock_id → code 매핑 (한 번에 조회)
        code_map = await self._stock_code_map([t.stock_id for t in trades])

        summary: dict[str, Any] = {
            "status": run.status,
            "period_from": run.period_from.isoformat(),
            "period_to": run.period_to.isoformat(),
            "initial_capital": str(run.initial_capital),
        }
        metrics: dict[str, Any] = {}
        equity_curve = None
        if result:
            metrics = dict(result.summary or {})
            metrics.update({
                "cumulative_return": _to_float(result.cumulative_return),
                "annualized_return": _to_float(result.annualized_return),
                "mdd": _to_float(result.mdd),
                "sharpe": _to_float(result.sharpe),
                "win_rate": _to_float(result.win_rate),
                "trade_count": result.trade_count,
            })
            equity_curve = result.equity_curve
            summary["label"] = result.label

        return {
            "job_id": str(run.job_id),
            "summary": summary,
            "equity_curve": equity_curve,
            "trades": [
                {
                    "code": code_map.get(t.stock_id, ""),
                    "side": t.side,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "qty": t.qty,
                    "pnl": t.pnl,
                    "entry_at": t.entry_at,
                    "exit_at": t.exit_at,
                }
                for t in trades
            ],
            "metrics": metrics,
        }

    async def list_trades(
        self, *, user_id: int, job_id: str, offset: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        """거래 내역 페이지네이션."""
        run = await self.get_run(user_id=user_id, job_id=job_id)
        stmt = (
            select(BacktestTrade)
            .where(BacktestTrade.run_id == run.id)
            .order_by(BacktestTrade.entry_at.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        cnt = (
            await self.db.execute(
                select(func.count(BacktestTrade.id)).where(BacktestTrade.run_id == run.id)
            )
        ).scalar_one()
        code_map = await self._stock_code_map([t.stock_id for t in rows])
        items = [
            {
                "code": code_map.get(t.stock_id, ""),
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "qty": t.qty,
                "pnl": t.pnl,
                "entry_at": t.entry_at,
                "exit_at": t.exit_at,
            }
            for t in rows
        ]
        return items, int(cnt or 0)

    async def save_result(self, *, user_id: int, job_id: str, label: str) -> BacktestResult:
        run = await self.get_run(user_id=user_id, job_id=job_id)
        result = await self.db.get(BacktestResult, run.id)
        if not result:
            raise AppException("E0031", message="저장할 결과가 없습니다.")
        result.label = label
        await self.db.commit()
        return result

    async def list_saved(
        self, user_id: int, *, offset: int, limit: int
    ) -> tuple[list[tuple[BacktestResult, BacktestRun]], int]:
        return await self.results.list_saved_for_user(user_id, offset=offset, limit=limit)

    async def compare(self, *, user_id: int, result_ids: list[str]) -> dict[str, Any]:
        out: list[dict[str, Any]] = []
        for jid in result_ids:
            try:
                run = await self.get_run(user_id=user_id, job_id=jid)
                result = await self.db.get(BacktestResult, run.id)
                if result:
                    out.append({
                        "job_id": jid,
                        "label": result.label,
                        "cumulative_return": result.cumulative_return,
                        "mdd": result.mdd,
                        "sharpe": result.sharpe,
                        "win_rate": result.win_rate,
                        "trade_count": result.trade_count,
                    })
            except AppException:
                continue
        return {"items": out, "count": len(out)}

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    async def _count_active_runs(self, user_id: int) -> int:
        stmt = select(func.count(BacktestRun.id)).where(
            BacktestRun.user_id == user_id,
            BacktestRun.status.in_(("QUEUED", "RUNNING")),
        )
        return int((await self.db.execute(stmt)).scalar_one() or 0)

    async def _stock_code_map(self, stock_ids: list[int]) -> dict[int, str]:
        ids = list({sid for sid in stock_ids if sid})
        if not ids:
            return {}
        stmt = select(Stock.id, Stock.code).where(Stock.id.in_(ids))
        return {sid: code for sid, code in (await self.db.execute(stmt)).all()}

    async def _run_inline(self, run: BacktestRun) -> None:
        """Celery 미가용 환경에서 동기적으로 백테스트 실행."""
        from app.services.backtest_engine.runner import run_backtest as engine_run
        from app.services.backtest_engine.config import BacktestConfig

        # 전략 정보 다시 로드 (entry/exit_rules)
        strategy = await self.db.get(
            (await self._strategy_model()),
            run.strategy_id,
        )

        strategy_type, params = self._select_strategy_payload(strategy)

        try:
            run.status = "RUNNING"
            run.started_at = datetime.now(tz=timezone.utc)
            await self.db.commit()

            config = BacktestConfig(
                universe=list(run.universe or []),
                strategy_type=strategy_type,
                strategy_id=run.strategy_id,
                period_from=run.period_from,
                period_to=run.period_to,
                initial_capital=run.initial_capital,
                fee_rate=run.fee_rate,
                slippage=run.slippage,
                strategy_params=params,
            )

            result = await engine_run(config, self.db, progress_cb=None)
            await persist_result(self.db, run, result)
            run.status = "DONE"
            run.progress = 100
            run.finished_at = datetime.now(tz=timezone.utc)
            await self.db.commit()
        except Exception as e:
            log.exception("backtest_inline_failed", error=str(e))
            run.status = "FAILED"
            run.error_message = str(e)[:500]
            run.finished_at = datetime.now(tz=timezone.utc)
            await self.db.commit()

    async def _strategy_model(self):
        from app.models.trade import Strategy
        return Strategy

    @staticmethod
    def _select_strategy_payload(strategy: Any) -> tuple[str, dict[str, Any]]:
        """전략 ORM → (strategy_type, params).

        meta.engine_type 이 명시되면 사용, 아니면 composite.
        """
        if strategy is None:
            return "golden_cross", {}
        entry = strategy.entry_rules or {}
        exit_ = strategy.exit_rules or {}
        # 명시적 엔진 지정 (옵션)
        if isinstance(strategy.limits, dict) and strategy.limits.get("engine_type"):
            etype = str(strategy.limits["engine_type"])
            return etype, dict(strategy.limits.get("engine_params") or {})
        if entry or exit_:
            return "composite", {"entry_rules": entry, "exit_rules": exit_}
        return "golden_cross", {}


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------
# 결과 영속화 (워커/inline 양쪽에서 재사용)
# ----------------------------------------------------------------------------
async def persist_result(db: AsyncSession, run: BacktestRun, engine_result: Any) -> None:
    """엔진 결과를 backtest_results + backtest_trades 로 저장."""
    metrics = engine_result.metrics
    summary = dict(engine_result.summary)
    summary["monthly_returns"] = engine_result.monthly_returns

    result = BacktestResult(
        run_id=run.id,
        label=None,
        cumulative_return=_decimal(metrics.get("cumulative_return")),
        annualized_return=_decimal(metrics.get("annualized_return")),
        mdd=_decimal(metrics.get("mdd"), q=4),
        sharpe=_decimal(metrics.get("sharpe")),
        win_rate=_decimal(metrics.get("win_rate"), q=4),
        trade_count=int(metrics.get("trade_count") or 0),
        equity_curve={"points": engine_result.equity_curve},
        summary=summary,
    )
    db.add(result)
    await db.flush()

    # 거래내역 저장
    if engine_result.trades:
        code_to_id = await _resolve_code_to_id(
            db, list({t.code for t in engine_result.trades})
        )
        for tr in engine_result.trades:
            stock_id = code_to_id.get(tr.code)
            if stock_id is None:
                continue
            db.add(
                BacktestTrade(
                    run_id=run.id,
                    stock_id=stock_id,
                    side=tr.side,
                    entry_price=tr.entry_price,
                    exit_price=tr.exit_price,
                    qty=Decimal(tr.qty),
                    pnl=tr.pnl,
                    entry_at=_as_datetime(tr.entry_at),
                    exit_at=_as_datetime(tr.exit_at),
                )
            )


async def _resolve_code_to_id(db: AsyncSession, codes: list[str]) -> dict[str, int]:
    if not codes:
        return {}
    stmt = select(Stock.id, Stock.code).where(Stock.code.in_(codes))
    return {code: sid for sid, code in (await db.execute(stmt)).all()}


def _decimal(value: Any, q: int = 8) -> Decimal | None:
    if value is None:
        return None
    try:
        fmt = f"{{:.{q}f}}"
        return Decimal(fmt.format(float(value)))
    except (TypeError, ValueError):
        return None


def _as_datetime(d: Any) -> datetime | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return None
