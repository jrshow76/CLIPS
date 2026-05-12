"""백테스트 서비스.

v1.0 동작:
- 잡 생성 시 BacktestRun ROW를 QUEUED 상태로 저장
- Celery `backtest.run` 태스크 큐잉 (워커가 실제 실행)
- 워커 미가용 시에도 동작을 시연하기 위해 mock 결과를 즉시 저장하는 fallback 포함
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.backtest import BacktestResult, BacktestRun
from app.repositories.backtest_repository import (
    BacktestResultRepository,
    BacktestRunRepository,
    BacktestTradeRepository,
)
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.stock_repository import StockExtRepository

log = structlog.get_logger(__name__)


# 입력 한도
MAX_PERIOD_DAYS = 365 * 3
MIN_CAPITAL = Decimal("100000")  # 10만원
MAX_CAPITAL = Decimal("10000000000")  # 100억


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
        if (to_date - from_date).days > MAX_PERIOD_DAYS:
            errors["period"] = [f"최대 {MAX_PERIOD_DAYS}일까지 허용됩니다."]
        if not (MIN_CAPITAL <= initial_capital <= MAX_CAPITAL):
            errors["initial_capital"] = ["허용 범위를 벗어났습니다."]
        if slippage < 0 or slippage > Decimal("0.1"):
            errors["slippage"] = ["0 ~ 0.1 사이여야 합니다."]
        if fee_rate < 0 or fee_rate > Decimal("0.01"):
            errors["fee_rate"] = ["0 ~ 0.01 사이여야 합니다."]
        if errors:
            raise AppException("E0032", details=errors)

        strategy = await self.strategies.find_by_public_id(strategy_public_id)
        if not strategy or strategy.user_id != user_id:
            raise AppException("E0062", message="전략을 찾을 수 없습니다.")

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

        # Celery 태스크 큐잉
        try:
            from app.workers.tasks.backtest_tasks import run_backtest as run_task

            run_task.delay(str(run.job_id))
        except Exception as e:
            log.warning("backtest_enqueue_celery_failed", error=str(e))
            # fallback: 즉시 mock 결과 생성 (시연용)
            await self._mock_finish(run)

        log.info("backtest_enqueued", user_id=user_id, job_id=str(run.job_id))
        return run

    # ------------------------------------------------------------------
    # 잡 조회
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
        run.status = "CANCELED"
        run.finished_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        return run

    async def get_result(self, *, user_id: int, job_id: str) -> dict[str, Any]:
        run = await self.get_run(user_id=user_id, job_id=job_id)
        # 결과 만료 (예: 30일)
        if run.finished_at and run.finished_at < datetime.now(tz=timezone.utc) - timedelta(days=30):
            raise AppException("E0031", message="백테스트 결과가 만료되었습니다.")
        result = await self.db.get(BacktestResult, run.id)
        trades = await self.trades.list_for_run(run.id)
        summary = {
            "status": run.status,
            "period_from": run.period_from.isoformat(),
            "period_to": run.period_to.isoformat(),
            "initial_capital": str(run.initial_capital),
        }
        metrics = {}
        equity_curve = None
        if result:
            metrics = result.summary or {}
            metrics["cumulative_return"] = result.cumulative_return
            metrics["annualized_return"] = result.annualized_return
            metrics["mdd"] = result.mdd
            metrics["sharpe"] = result.sharpe
            metrics["win_rate"] = result.win_rate
            metrics["trade_count"] = result.trade_count
            equity_curve = result.equity_curve
            summary["label"] = result.label
        return {
            "job_id": str(run.job_id),
            "summary": summary,
            "equity_curve": equity_curve,
            "trades": [
                {
                    "code": "",  # stock_id → code 매핑은 비용↑이므로 단순화: 빈 문자열
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
                    out.append(
                        {
                            "job_id": jid,
                            "label": result.label,
                            "cumulative_return": result.cumulative_return,
                            "mdd": result.mdd,
                            "sharpe": result.sharpe,
                            "win_rate": result.win_rate,
                            "trade_count": result.trade_count,
                        }
                    )
            except AppException:
                continue
        return {"items": out, "count": len(out)}

    # ------------------------------------------------------------------
    # 내부: mock 결과 생성 (Celery 워커 미가용 시)
    # ------------------------------------------------------------------
    async def _mock_finish(self, run: BacktestRun) -> None:
        """워커 미가용 환경에서 동작을 시연하기 위한 mock 결과."""
        now = datetime.now(tz=timezone.utc)
        run.status = "DONE"
        run.progress = 100
        run.started_at = now
        run.finished_at = now

        # mock 결과
        result = BacktestResult(
            run_id=run.id,
            label=None,
            cumulative_return=Decimal("0.1234"),
            annualized_return=Decimal("0.1500"),
            mdd=Decimal("-0.0823"),
            sharpe=Decimal("1.42"),
            win_rate=Decimal("0.5500"),
            trade_count=42,
            equity_curve={
                "ts": [run.period_from.isoformat(), run.period_to.isoformat()],
                "value": [
                    float(run.initial_capital),
                    float(run.initial_capital) * 1.1234,
                ],
            },
            summary={"engine": "mock", "note": "Celery 워커 미가용 환경 fallback"},
        )
        self.db.add(result)
        await self.db.commit()
