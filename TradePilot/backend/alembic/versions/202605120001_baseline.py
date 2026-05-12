"""baseline (DDL은 database/init/*.sql이 1차 소스).

Revision ID: 202605120001
Revises:
Create Date: 2026-05-12 00:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

# revision identifiers
revision: str = "202605120001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op: 모든 스키마와 테이블은 database/init/*.sql 로 이미 관리된다.

    이후 Alembic 리비전은 DDL 증분 변경에만 사용한다.
    """
    pass


def downgrade() -> None:
    """No-op."""
    pass
