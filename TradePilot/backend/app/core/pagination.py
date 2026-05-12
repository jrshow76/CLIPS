"""페이지네이션 유틸.

`docs/24_api_response_spec.md` §7 규약을 따른다.
- page: 1-based
- size: 기본 20, 최대 100
- sort: `field,asc|desc` 콤마 구분 (다중 정렬 가능)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Query

DEFAULT_PAGE = 1
DEFAULT_SIZE = 20
MAX_SIZE = 100


@dataclass
class PageParams:
    """페이지네이션 파라미터 묶음."""

    page: int = DEFAULT_PAGE
    size: int = DEFAULT_SIZE
    sort: list[str] | None = None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def page_params(
    page: Annotated[int, Query(ge=1, description="페이지 번호(1-based)")] = DEFAULT_PAGE,
    size: Annotated[
        int, Query(ge=1, le=MAX_SIZE, description="페이지 크기 (최대 100)")
    ] = DEFAULT_SIZE,
    sort: Annotated[
        list[str] | None,
        Query(description="정렬: `field,asc|desc` (반복 가능)"),
    ] = None,
) -> PageParams:
    """FastAPI Depends 페이지 파라미터."""
    return PageParams(page=page, size=size, sort=sort or None)


def parse_sort(sort_items: list[str] | None, allow_fields: set[str]) -> list[tuple[str, str]]:
    """sort 쿼리 파싱.

    예: ["score,desc", "volume,desc"] → [("score","desc"), ("volume","desc")]
    화이트리스트(`allow_fields`)에 없는 필드는 무시한다.
    """
    if not sort_items:
        return []
    parsed: list[tuple[str, str]] = []
    for raw in sort_items:
        parts = raw.split(",")
        field = parts[0].strip()
        direction = (parts[1].strip().lower() if len(parts) > 1 else "asc")
        if direction not in ("asc", "desc"):
            direction = "asc"
        if field in allow_fields:
            parsed.append((field, direction))
    return parsed


def compute_has_next(total: int | None, page: int, size: int, fetched: int) -> bool:
    """다음 페이지 존재 여부."""
    if total is None:
        return fetched >= size
    return page * size < total
