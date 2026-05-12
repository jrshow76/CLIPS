"""백테스트 워커 태스크.

큐: `backtest`.

진행률 단계:
    데이터로드 10% → 지표계산 30% → 시뮬레이션 80% → 메트릭저장 100%

장애 처리:
- 엔진 예외 시 status=FAILED 로 마킹, error_message 저장.
- max_retries=2 (네트워크/DB 일시 장애 대비).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


@shared_task(
    name="backtest.run",
    queue="backtest",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def run_backtest(self, job_id: str) -> dict[str, Any]:
    """백테스트 실행 태스크 (실 엔진)."""
    log.info("backtest_run_started", job_id=job_id)
    try:
        result = asyncio.run(_run_async(job_id))
    except Exception as exc:  # noqa: BLE001 - Celery 재시도 흐름
        log.exception("backtest_run_error", job_id=job_id, error=str(exc))
        # FAILED 상태 마킹 후 재시도
        asyncio.run(_mark_failed(job_id, str(exc)[:500]))
        raise self.retry(exc=exc)
    log.info("backtest_run_finished", job_id=job_id, status=result.get("status"))
    return result


async def _run_async(job_id: str) -> dict[str, Any]:
    """비동기 본체.

    1) BacktestRun 조회 및 RUNNING 마킹
    2) 엔진 실행 (진행률 콜백 → progress 컬럼 갱신)
    3) 결과 저장 + DONE 마킹
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.backtest import BacktestRun
    from app.services.backtest_engine import BacktestConfig, run_backtest as engine_run
    from app.services.backtest_service import persist_result

    async with AsyncSessionLocal() as db:
        stmt = select(BacktestRun).where(BacktestRun.job_id == job_id)
        run = (await db.execute(stmt)).scalar_one_or_none()
        if not run:
            log.warning("backtest_run_not_found", job_id=job_id)
            return {"job_id": job_id, "status": "NOT_FOUND"}

        if run.status == "CANCELED":
            return {"job_id": job_id, "status": "CANCELED"}

        # RUNNING 마킹
        run.status = "RUNNING"
        run.progress = 5
        run.started_at = datetime.now(tz=timezone.utc)
        await db.commit()

        # 전략 로드
        from app.models.trade import Strategy
        strategy = await db.get(Strategy, run.strategy_id)
        strategy_type, params = _strategy_payload(strategy)

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

        # 진행률 콜백: DB 갱신 비용을 줄이기 위해 5% 단위로만 commit
        last_pct: list[int] = [run.progress]

        def progress_cb(pct: int) -> None:
            if pct - last_pct[0] >= 5 or pct >= 100:
                last_pct[0] = pct
                try:
                    asyncio.create_task(_update_progress(job_id, pct))
                except RuntimeError:
                    # 동기 컨텍스트(예: 단위 테스트)에서는 best-effort skip
                    pass

        engine_result = await engine_run(config, db, progress_cb=progress_cb)

        # 결과 영속화
        await persist_result(db, run, engine_result)
        run.status = "DONE"
        run.progress = 100
        run.finished_at = datetime.now(tz=timezone.utc)
        await db.commit()

        return {
            "job_id": job_id,
            "status": "DONE",
            "trade_count": int(engine_result.metrics.get("trade_count") or 0),
            "cumulative_return": engine_result.metrics.get("cumulative_return"),
        }


async def _update_progress(job_id: str, pct: int) -> None:
    """진행률만 짧은 트랜잭션으로 갱신."""
    from sqlalchemy import update

    from app.core.database import AsyncSessionLocal
    from app.models.backtest import BacktestRun

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(BacktestRun)
            .where(BacktestRun.job_id == job_id)
            .values(progress=pct)
        )
        await db.commit()


async def _mark_failed(job_id: str, message: str) -> None:
    from sqlalchemy import update

    from app.core.database import AsyncSessionLocal
    from app.models.backtest import BacktestRun

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(BacktestRun)
            .where(BacktestRun.job_id == job_id)
            .values(
                status="FAILED",
                error_message=message,
                finished_at=datetime.now(tz=timezone.utc),
            )
        )
        await db.commit()


def _strategy_payload(strategy: Any) -> tuple[str, dict[str, Any]]:
    """전략 ORM → (engine type, params)."""
    if strategy is None:
        return "golden_cross", {}
    limits = strategy.limits or {}
    if isinstance(limits, dict) and limits.get("engine_type"):
        return str(limits["engine_type"]), dict(limits.get("engine_params") or {})
    if strategy.entry_rules or strategy.exit_rules:
        return "composite", {
            "entry_rules": strategy.entry_rules or {},
            "exit_rules": strategy.exit_rules or {},
        }
    return "golden_cross", {}
