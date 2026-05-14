"""Celery 인스턴스.

7개 큐: default, signals, orders, backtest, ml, notifications, ingestion.
워커 실행:
    celery -A app.workers.celery_app worker --loglevel=INFO \
      -Q signals,orders,backtest,ml,notifications,ingestion,default
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab  # type: ignore
from kombu import Queue  # type: ignore

from app.core.config import settings


def _cron(hour: int, minute: int):
    """월~금 KST 시간 cron 헬퍼."""
    return crontab(hour=hour, minute=minute, day_of_week="1-5")

celery_app = Celery(
    "tradepilot",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_RESULT_URL,
    include=[
        "app.workers.tasks.indicator_tasks",
        "app.workers.tasks.signal_tasks",
        "app.workers.tasks.order_tasks",
        "app.workers.tasks.backtest_tasks",
        "app.workers.tasks.ml_tasks",
        "app.workers.tasks.calendar_tasks",
        "app.workers.tasks.ingestion_tasks",
        "app.workers.tasks.cleanup_tasks",
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
        Queue("ingestion"),
    ],
    task_routes={
        "signals.*": {"queue": "signals"},
        "orders.*": {"queue": "orders"},
        "backtest.*": {"queue": "backtest"},
        "ml.*": {"queue": "ml"},
        "notifications.*": {"queue": "notifications"},
        "indicators.*": {"queue": "signals"},  # 시그널 큐 공용
        "calendar.*": {"queue": "default"},  # 캘린더 동기화 (저빈도)
        "ingestion.*": {"queue": "ingestion"},  # 시장 데이터 적재
        "cleanup.*": {"queue": "default"},  # 정리 작업 (저빈도)
    },
    worker_max_tasks_per_child=500,
    broker_connection_retry_on_startup=True,
)


# ---------------------------------------------------------------------------
# Beat 스케줄: 한국 장 시간 기준 ML 일괄 추론
# ---------------------------------------------------------------------------
# - 매일 KST 09:05 (장 개장 직후): 모든 활성 종목에 대해 1일 호라이즌 추론
# - 매일 KST 14:30 (장 마감 전):   1/3/5일 호라이즌 모두 갱신
# 타임존은 conf.timezone(APP_TIMEZONE) 기준 (기본 Asia/Seoul)
celery_app.conf.beat_schedule = {
    "ml-batch-predict-morning": {
        "task": "ml.batch_predict",
        "schedule": _cron(hour=9, minute=5),
        "kwargs": {"horizons": [1]},
        "options": {"queue": "ml"},
    },
    "ml-batch-predict-afternoon": {
        "task": "ml.batch_predict",
        "schedule": _cron(hour=14, minute=30),
        "kwargs": {"horizons": [1, 3, 5]},
        "options": {"queue": "ml"},
    },
    # 매년 1월 2일 09:00 KST: 당해/익년 휴장일 자동 동기화
    # day_of_week='*' 로 평일 제한을 풀어 1/2 가 토/일이어도 실행되도록 한다.
    "calendar-sync-yearly": {
        "task": "calendar.sync_yearly",
        "schedule": crontab(month_of_year="1", day_of_month="2", hour="9", minute="0"),
        "options": {"queue": "default"},
    },
    # ----------------------------------------------------------------------
    # 데이터 적재 스케줄 (KST 기준)
    # ----------------------------------------------------------------------
    # 매일 08:00: KRX 종목 마스터 + 섹터 매핑 동기화 (장 개장 전)
    "ingest-stock-master": {
        "task": "ingestion.stock_master",
        "schedule": _cron(hour=8, minute=0),
        "options": {"queue": "ingestion"},
    },
    # 매일 16:30: 전일 일봉 적재 (장 마감 후 30분, 정합성 시점)
    "ingest-daily-prices": {
        "task": "ingestion.daily_prices",
        "schedule": _cron(hour=16, minute=30),
        "options": {"queue": "ingestion"},
    },
    # 매일 16:30: KOSPI/KOSDAQ/KOSPI200 지수 일봉
    "ingest-market-indices": {
        "task": "ingestion.market_indices",
        "schedule": _cron(hour=16, minute=35),
        "options": {"queue": "ingestion"},
    },
    # 장중 09:00 ~ 15:30 / 5분 간격: 활성 종목 분봉 적재 (게이트웨이 가용 시)
    "ingest-minute-prices-active": {
        "task": "ingestion.minute_prices",
        "schedule": crontab(
            minute="*/5",
            hour="9-15",
            day_of_week="1-5",
        ),
        "options": {"queue": "ingestion"},
    },
    # 매일 23:30: 다음 달 분봉 파티션 사전 생성 (월말에도 안전)
    "ingest-ensure-minute-partitions": {
        "task": "ingestion.ensure_minute_partitions",
        "schedule": crontab(hour="23", minute="30"),
        "kwargs": {"months": 2},
        "options": {"queue": "ingestion"},
    },
    # ----------------------------------------------------------------------
    # SEC-003(GATE-1): Kill Switch 부분 실패 재시도 — 5분 주기
    # ----------------------------------------------------------------------
    "orders-kill-switch-retry": {
        "task": "orders.kill_switch_retry",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "orders"},
    },
    # ----------------------------------------------------------------------
    # SEC-004(GATE-3): 만료된 refresh 세션 정리 — 매일 04:00 KST
    # ----------------------------------------------------------------------
    "cleanup-refresh-sessions": {
        "task": "cleanup.refresh_sessions",
        "schedule": crontab(hour="4", minute="0"),
        "options": {"queue": "default"},
    },
}


# 기본 빈 디스커버리 호환을 위한 placeholder
@celery_app.task(name="ping")
def ping() -> str:
    return "pong"
