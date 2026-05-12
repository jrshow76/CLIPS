"""백테스트 워커 태스크.

v1.0은 mock 실행만 수행하며, 실제 백테스트 엔진은 향후 확장 예정.
큐: `backtest`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(name="backtest.run", queue="backtest", bind=True)
def run_backtest(self, job_id: str) -> dict[str, Any]:
    """백테스트 실행 태스크.

    실제 엔진 구현 전까지는 BacktestRun을 DONE으로 마킹하고 mock 결과를 저장한다.
    """
    log.info("backtest_run_started", job_id=job_id)

    # 동기 컨텍스트에서 비동기 DB 작업: 별도 sync 세션 또는 asyncio.run 활용
    import asyncio

    asyncio.run(_run_async(job_id))
    log.info("backtest_run_finished", job_id=job_id)
    return {"job_id": job_id, "status": "DONE"}


async def _run_async(job_id: str) -> None:
    """비동기 DB 작업 본체."""
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.backtest import BacktestResult, BacktestRun

    async with AsyncSessionLocal() as db:
        stmt = select(BacktestRun).where(BacktestRun.job_id == job_id)
        run = (await db.execute(stmt)).scalar_one_or_none()
        if not run:
            return

        run.status = "RUNNING"
        run.progress = 50
        run.started_at = datetime.now(tz=timezone.utc)
        await db.commit()

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
            summary={"engine": "mock-v1"},
        )
        db.add(result)
        run.status = "DONE"
        run.progress = 100
        run.finished_at = datetime.now(tz=timezone.utc)
        await db.commit()
