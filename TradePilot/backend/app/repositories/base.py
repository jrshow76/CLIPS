"""Repository 베이스 클래스.

`BackendDev`가 새 도메인 추가 시 본 클래스를 상속해 구현한다.
- 모든 메서드는 async.
- 트랜잭션 commit/rollback은 서비스 레이어 책임 (Repository는 flush까지만).
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """모든 Repository의 공통 베이스."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: Any) -> ModelT | None:
        """PK 기반 단건 조회."""
        return await self.session.get(self.model, id)

    async def get_by(self, **kwargs: Any) -> ModelT | None:
        """단일 컬럼 필터 단건 조회."""
        stmt = select(self.model).filter_by(**kwargs).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by(self, *, limit: int | None = None, **kwargs: Any) -> list[ModelT]:
        """단순 필터 리스트 조회."""
        stmt = select(self.model).filter_by(**kwargs)
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, instance: ModelT) -> ModelT:
        """저장 (flush)."""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def remove(self, id: Any) -> None:
        """삭제."""
        await self.session.execute(delete(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
