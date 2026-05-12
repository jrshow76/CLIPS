"""APScheduler 스케줄러 진입점.

docker-compose backend-scheduler 컨테이너에서 `python -m app.scheduler_app`로 실행.

스케줄 (docs/21 §3.7):
- pre_market_warmup: 평일 08:30
- signal_pulse: 평일 09:00~15:20 / 5초
- cancel_stale_orders: 평일 15:25
- daily_report: 평일 15:35
- ml_retrain: 평일 18:00
- master_refresh: 매일 06:00
"""
from __future__ import annotations

import asyncio
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


def _enqueue_signal_evaluation() -> None:
    """5초 주기 시그널 평가 enqueue."""
    try:
        from app.workers.celery_app import celery_app
        celery_app.send_task("signals.evaluate", queue="signals")
    except Exception:
        log.exception("signal_pulse_enqueue_failed")


def _enqueue_daily_indicator() -> None:
    try:
        from app.workers.celery_app import celery_app
        celery_app.send_task("indicators.compute_daily", queue="signals")
    except Exception:
        log.exception("daily_indicator_enqueue_failed")


def build_scheduler() -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="Asia/Seoul")

    # 평일 5초 시그널 펄스
    sched.add_job(
        _enqueue_signal_evaluation,
        IntervalTrigger(seconds=5),
        id="signal_pulse",
        replace_existing=True,
    )

    # 일별 지표 배치 (장 마감 후 16:30)
    sched.add_job(
        _enqueue_daily_indicator,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=30),
        id="indicator_daily",
        replace_existing=True,
    )

    return sched


async def main() -> None:
    configure_logging()
    log.info("scheduler_start")
    sched = build_scheduler()
    sched.start()

    stop = asyncio.Event()

    def _signal_handler() -> None:
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    await stop.wait()
    sched.shutdown(wait=False)
    log.info("scheduler_stop")


if __name__ == "__main__":
    asyncio.run(main())
