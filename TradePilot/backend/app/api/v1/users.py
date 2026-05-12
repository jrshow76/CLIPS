"""사용자 API 라우터.

`docs/13_api_requirements.md` §2 명세 구현.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, require_role
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.schemas.user import (
    AdminUserItem,
    RoleUpdateIn,
    UserMeOut,
    UserMeUpdateIn,
    UserSettingsOut,
    UserSettingsUpdateIn,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _to_me(user) -> UserMeOut:
    return UserMeOut(
        id=str(user.public_id),
        email=user.email,
        nickname=user.nickname,
        role=user.role,
        trade_mode=user.trade_mode,
        phone=user.phone,
        email_verified=user.email_verified,
        phone_verified=user.phone_verified,
        created_at=user.created_at.isoformat(),
    )


@router.get("/me", summary="내 정보 조회")
async def get_me(user: CurrentUser):
    return success_response(_to_me(user))


@router.patch("/me", summary="내 정보 수정")
async def patch_me(
    payload: UserMeUpdateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    updated = await svc.update_me(user, nickname=payload.nickname, phone=payload.phone)
    return success_response(_to_me(updated))


@router.get("/me/settings", summary="내 설정 조회")
async def get_my_settings(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = UserService(db)
    s = await svc.get_settings(user.id)
    return success_response(
        UserSettingsOut(
            theme=s.theme,  # type: ignore[arg-type]
            noti_inapp=s.noti_inapp,
            noti_email=s.noti_email,
            noti_telegram=s.noti_telegram,
            noti_rules=s.noti_rules or {},
            schedule=s.schedule or {},
        )
    )


@router.patch("/me/settings", summary="내 설정 수정")
async def patch_my_settings(
    payload: UserSettingsUpdateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    s = await svc.update_settings(
        user.id,
        theme=payload.theme,
        noti_inapp=payload.noti_inapp,
        noti_email=payload.noti_email,
        noti_telegram=payload.noti_telegram,
        noti_rules=payload.noti_rules,
        schedule=payload.schedule,
    )
    return success_response(
        UserSettingsOut(
            theme=s.theme,  # type: ignore[arg-type]
            noti_inapp=s.noti_inapp,
            noti_email=s.noti_email,
            noti_telegram=s.noti_telegram,
            noti_rules=s.noti_rules or {},
            schedule=s.schedule or {},
        )
    )


# ---------------------------------------------------------------------------
# 관리자 API
# ---------------------------------------------------------------------------
@router.get("", summary="(ADMIN) 사용자 목록")
async def list_users_admin(
    _admin=Depends(require_role("ROLE_ADMIN")),
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    q: str | None = Query(None, description="이메일/닉네임 검색"),
    role: str | None = Query(None),
):
    svc = UserService(db)
    rows, total = await svc.list_users_admin(
        q=q, role=role, offset=page.offset, limit=page.limit
    )
    items = [
        AdminUserItem(
            id=str(u.public_id),
            email=u.email,
            nickname=u.nickname,
            role=u.role,
            trade_mode=u.trade_mode,
            created_at=u.created_at.isoformat(),
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in rows
    ]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.patch("/{user_public_id}/role", summary="(ADMIN) 사용자 역할 변경")
async def update_role(
    user_public_id: str,
    payload: RoleUpdateIn,
    _admin=Depends(require_role("ROLE_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    updated = await svc.update_role_admin(user_public_id, payload.role)
    return success_response({"id": str(updated.public_id), "role": updated.role})
