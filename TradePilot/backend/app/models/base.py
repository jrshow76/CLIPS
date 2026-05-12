"""ORM 베이스 클래스.

PostgreSQL 스키마 분리(tp_user, tp_market, ...)를 적용하므로, 각 모델 클래스는
`__table_args__ = {"schema": "tp_xxx"}` 를 지정한다.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """모든 ORM 모델의 베이스."""

    pass


# 자주 쓰는 timestamptz 타입 단축
TimestampTZ = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now()),
]


class TimestampMixin:
    """created_at / updated_at 컬럼 자동 부여."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
