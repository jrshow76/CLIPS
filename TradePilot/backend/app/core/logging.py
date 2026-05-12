"""구조화 로깅 설정.

structlog 기반으로 JSON 로그를 출력하고, trace_id 컨텍스트를 자동으로 포함한다.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """애플리케이션 시작 시 1회 호출하는 로깅 설정."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=False)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_dev:
        # 개발 환경은 사람이 읽기 쉬운 컬러 출력
        renderer: Any = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # 운영 환경은 JSON
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # 표준 logging도 동일 수준으로 맞춤 (sqlalchemy/uvicorn 등)
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    # 시끄러운 라이브러리 톤다운
    for noisy in ("uvicorn.access", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    """모듈 단위 로거 헬퍼."""
    return structlog.get_logger(name) if name else structlog.get_logger()


def bind_trace(trace_id: str, **kwargs: Any) -> None:
    """현재 요청 컨텍스트에 trace_id 를 바인딩한다."""
    structlog.contextvars.bind_contextvars(trace_id=trace_id, **kwargs)


def clear_trace() -> None:
    """요청 종료 시 컨텍스트를 비운다."""
    structlog.contextvars.clear_contextvars()
