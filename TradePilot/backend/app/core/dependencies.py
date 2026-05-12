"""FastAPI 공통 Depends.

- get_current_user: JWT 검증 → User ORM 반환
- get_trade_mode: X-Trade-Mode 헤더 검증
- require_role: 역할 가드 데코레이터
- get_idempotency_key: X-Idempotency-Key 헤더 (옵션)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.security import decode_jwt_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT access 토큰을 검증하고 활성 사용자 ORM 객체를 반환한다."""
    if not token:
        raise AppException("E0001", message="인증이 필요합니다.")

    payload = decode_jwt_token(token, expected_type="access")
    public_id = payload.get("sub")
    if not public_id:
        raise AppException("E0001", message="인증 토큰이 유효하지 않습니다.")

    stmt = select(User).where(User.public_id == public_id, User.deleted_at.is_(None))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise AppException("E0001", message="사용자를 찾을 수 없습니다.")

    # 계정 잠금 확인
    from datetime import datetime, timezone
    if user.locked_until and user.locked_until > datetime.now(tz=timezone.utc):
        raise AppException("E0052", message="계정이 잠겨있습니다.")

    request.state.user_id = user.id
    request.state.user_public_id = user.public_id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """인증이 선택적인 엔드포인트용."""
    if not token:
        return None
    try:
        return await get_current_user(request, token, db)
    except AppException:
        return None


# ---------------------------------------------------------------------------
# X-Trade-Mode 가드 (docs/24 §5)
# ---------------------------------------------------------------------------
async def require_trade_mode(
    x_trade_mode: Annotated[str, Header(alias="X-Trade-Mode")],
    user: CurrentUser,
) -> str:
    """주문/모드 변경 API의 X-Trade-Mode 검증.

    - 누락/비정상 값 → E0003
    - 사용자 모드와 불일치 → E0006
    - LIVE 권한 없는 사용자가 LIVE 요청 → E0002
    """
    mode = x_trade_mode.strip().upper()
    if mode not in ("SIM", "LIVE"):
        raise AppException(
            "E0003",
            message="X-Trade-Mode 헤더는 SIM 또는 LIVE 여야 합니다.",
            details={"X-Trade-Mode": ["허용되지 않은 값입니다."]},
        )
    if user.trade_mode != mode:
        raise AppException(
            "E0006",
            details={"header_mode": mode, "user_mode": user.trade_mode},
        )
    if mode == "LIVE" and user.role not in ("ROLE_TRADER_PRO", "ROLE_ADMIN"):
        raise AppException("E0002", message="실거래 권한이 없습니다.")
    return mode


TradeModeDep = Annotated[str, Depends(require_trade_mode)]


# ---------------------------------------------------------------------------
# 역할 가드
# ---------------------------------------------------------------------------
def require_role(*allowed_roles: str):
    """역할(role) 가드. 예: Depends(require_role('ROLE_ADMIN'))."""

    async def _checker(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise AppException(
                "E0092" if "ROLE_ADMIN" in allowed_roles else "E0002",
                message="권한이 없습니다.",
                details={"required": list(allowed_roles), "current": user.role},
            )
        return user

    return _checker


# ---------------------------------------------------------------------------
# 멱등성 키
# ---------------------------------------------------------------------------
async def get_idempotency_key(
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
) -> str | None:
    return x_idempotency_key
