"""Celery 인스턴스.

5개 큐: default, signals, orders, backtest, ml, notifications.
워커 실행:
    celery -A app.workers.celery_app worker --loglevel=INFO -Q signals,orders,backtest,ml,notifications,default
"""
from __future__ import annotations

from celery import Celery
from kombu import Queue  # type: ignore

from app.core.config import settings

celery_app = Celery(
    "tradepilot",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_RESULT_URL,
    include=[
        "app.workers.tasks.indicator_tasks",
        "app.workers.tasks.signal_tasks",
        "app.workers.tasks.order_tasks",
        "app.workers.tasks.backtest_tasks",
    ],
)

celery_app.conf.update(
    timezone=settings.APP_TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_default_queue="default",
    task_queues=[
        Queue("default"),
        Queue("signals"),
        Queue("orders"),
        Queue("backtest"),
        Queue("ml"),
        Queue("notifications"),
    ],
    task_routes={
        "signals.*": {"queue": "signals"},
        "orders.*": {"queue": "orders"},
        "backtest.*": {"queue": "backtest"},
        "ml.*": {"queue": "ml"},
        "notifications.*": {"queue": "notifications"},
        "indicators.*": {"queue": "signals"},  # 시그널 큐 공용
    },
    worker_max_tasks_per_child=500,
    broker_connection_retry_on_startup=True,
)


# 기본 빈 디스커버리 호환을 위한 placeholder
@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
