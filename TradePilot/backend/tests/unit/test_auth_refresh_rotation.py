"""AuthService refresh 회전 단위 테스트 — SEC-004(GATE-3).

DB/Redis 없이 mock으로 다음을 검증한다:
1. /auth/refresh 호출 시 새 access + 새 refresh 발급 (회전)
2. 기존 세션은 revoked_at + replaced_by_jti 가 갱신됨 (회전 체인)
3. 동일 refresh 두 번째 호출 시 REPLAY 탐지 → 전 세션 폐기 + Redis publish
4. refresh 토큰에 jti 클레임이 포함됨
5. logout(refresh_token=...) 시 해당 세션만 폐기
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import AppException
from app.core.security import (
    create_jwt_token,
    create_refresh_token_with_jti,
    decode_jwt_token,
    hash_refresh_token,
)


def test_refresh_token_with_jti_includes_jti_claim():
    """SEC-004: 발급된 refresh 토큰의 JWT 페이로드에 jti 클레임이 포함되어야 한다."""
    token, jti, ttl = create_refresh_token_with_jti(subject=str(uuid4()))
    payload = decode_jwt_token(token, expected_type="refresh")
    assert payload["jti"] == jti
    assert payload["type"] == "refresh"
    assert ttl > 0


# ---------------------------------------------------------------------------
# AuthService.refresh — 회전 (정상)
# ---------------------------------------------------------------------------
def test_auth_refresh_rotates_and_revokes_old_session():
    """정상 refresh: 새 토큰 발급 + 기존 세션 revoked + replaced_by_jti 기록."""
    from app.services import auth_service as auth_mod

    public_id = str(uuid4())
    user = MagicMock()
    user.id = 42
    user.public_id = UUID(public_id)
    user.role = "ROLE_TRADER"
    user.trade_mode = "SIM"

    old_token, old_jti, ttl = create_refresh_token_with_jti(subject=public_id)
    old_session = MagicMock()
    old_session.id = 999
    old_session.user_id = user.id
    old_session.jti = UUID(old_jti)
    old_session.revoked_at = None
    old_session.expires_at = datetime.now(tz=timezone.utc) + timedelta(days=7)
    old_session.user_agent = "pytest"
    old_session.ip_address = None
    old_session.device_id = None

    # AsyncSession mock — commit only
    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()

    rotate_call = {}

    async def _rotate(sess, new_jti):
        rotate_call["session_id"] = sess.id
        rotate_call["new_jti"] = new_jti
        sess.revoked_at = datetime.now(tz=timezone.utc)
        sess.replaced_by_jti = UUID(new_jti) if isinstance(new_jti, str) else new_jti

    sessions_repo = MagicMock()
    sessions_repo.find_by_jti = AsyncMock(return_value=old_session)
    sessions_repo.add = AsyncMock()
    sessions_repo.rotate = AsyncMock(side_effect=_rotate)
    sessions_repo.revoke_all_for_user = AsyncMock()
    users_repo = MagicMock()
    users_repo.find_by_public_id = AsyncMock(return_value=user)

    async def _run():
        with patch.object(
            auth_mod, "UserRepository", return_value=users_repo
        ), patch.object(
            auth_mod, "SessionRepository", return_value=sessions_repo
        ), patch.object(auth_mod, "OtpRepository", return_value=MagicMock()):
            with patch.object(auth_mod, "get_redis", return_value=MagicMock(publish=AsyncMock())):
                svc = auth_mod.AuthService(db)
                return await svc.refresh(old_token)

    access, new_refresh, access_ttl, refresh_ttl = asyncio.run(_run())

    # 1) 회전 확인
    assert rotate_call["session_id"] == 999
    new_payload = decode_jwt_token(new_refresh, expected_type="refresh")
    assert new_payload["jti"] == rotate_call["new_jti"]
    # 2) 기존 세션 폐기 흔적
    assert old_session.revoked_at is not None
    # 3) 새 access 토큰도 sub 동일
    access_payload = decode_jwt_token(access, expected_type="access")
    assert access_payload["sub"] == public_id


# ---------------------------------------------------------------------------
# AuthService.refresh — REPLAY 탐지
# ---------------------------------------------------------------------------
def test_auth_refresh_replay_revokes_all_sessions_and_publishes_event():
    """이미 revoked된 jti가 다시 들어오면 REPLAY로 간주, 전 세션 폐기 + Redis publish."""
    from app.services import auth_service as auth_mod

    public_id = str(uuid4())
    user = MagicMock()
    user.id = 7
    user.public_id = UUID(public_id)
    user.role = "ROLE_TRADER"
    user.trade_mode = "SIM"

    leaked_token, leaked_jti, _ttl = create_refresh_token_with_jti(subject=public_id)
    revoked_session = MagicMock()
    revoked_session.id = 555
    revoked_session.user_id = user.id
    revoked_session.jti = UUID(leaked_jti)
    revoked_session.revoked_at = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    revoked_session.expires_at = datetime.now(tz=timezone.utc) + timedelta(days=6)

    db = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()

    sessions_repo = MagicMock()
    sessions_repo.find_by_jti = AsyncMock(return_value=revoked_session)
    sessions_repo.revoke_all_for_user = AsyncMock()
    users_repo = MagicMock()
    users_repo.find_by_public_id = AsyncMock(return_value=user)

    publish_mock = AsyncMock()
    redis_mock = MagicMock(publish=publish_mock)

    async def _run():
        with patch.object(
            auth_mod, "UserRepository", return_value=users_repo
        ), patch.object(
            auth_mod, "SessionRepository", return_value=sessions_repo
        ), patch.object(auth_mod, "OtpRepository", return_value=MagicMock()), patch.object(
            auth_mod, "get_redis", return_value=redis_mock
        ):
            svc = auth_mod.AuthService(db)
            with pytest.raises(AppException) as ei:
                await svc.refresh(leaked_token)
            return ei.value

    err = asyncio.run(_run())
    assert err.code == "E0001"
    # 전 세션 폐기 호출
    sessions_repo.revoke_all_for_user.assert_awaited_with(user.id)
    # Redis 보안 이벤트 publish
    assert publish_mock.await_count >= 1
    assert publish_mock.await_args.args[0] == "tp:security.events"


# ---------------------------------------------------------------------------
# AuthService.refresh — 만료된 세션
# ---------------------------------------------------------------------------
def test_auth_refresh_expired_session_returns_E0053():
    from app.services import auth_service as auth_mod

    public_id = str(uuid4())
    user = MagicMock(id=11, public_id=UUID(public_id), role="ROLE_TRADER", trade_mode="SIM")

    token, jti, _ = create_refresh_token_with_jti(subject=public_id)
    sess = MagicMock()
    sess.id = 1
    sess.user_id = user.id
    sess.jti = UUID(jti)
    sess.revoked_at = None
    sess.expires_at = datetime.now(tz=timezone.utc) - timedelta(seconds=10)

    db = MagicMock(commit=AsyncMock(), execute=AsyncMock())
    sessions_repo = MagicMock()
    sessions_repo.find_by_jti = AsyncMock(return_value=sess)
    users_repo = MagicMock()
    users_repo.find_by_public_id = AsyncMock(return_value=user)

    async def _run():
        with patch.object(auth_mod, "UserRepository", return_value=users_repo), patch.object(
            auth_mod, "SessionRepository", return_value=sessions_repo
        ), patch.object(auth_mod, "OtpRepository", return_value=MagicMock()), patch.object(
            auth_mod, "get_redis", return_value=MagicMock(publish=AsyncMock())
        ):
            svc = auth_mod.AuthService(db)
            with pytest.raises(AppException) as ei:
                await svc.refresh(token)
            return ei.value

    err = asyncio.run(_run())
    assert err.code == "E0053"


# ---------------------------------------------------------------------------
# logout — refresh_token이 있으면 해당 세션만 폐기
# ---------------------------------------------------------------------------
def test_logout_with_refresh_token_revokes_only_that_session():
    from app.services import auth_service as auth_mod

    public_id = str(uuid4())
    token, jti, _ = create_refresh_token_with_jti(subject=public_id)

    sess = MagicMock()
    sess.id = 7
    sess.user_id = 99
    sess.jti = UUID(jti)
    sess.revoked_at = None

    db = MagicMock(commit=AsyncMock())
    sessions_repo = MagicMock()
    sessions_repo.find_by_jti = AsyncMock(return_value=sess)
    sessions_repo.revoke = AsyncMock()
    sessions_repo.revoke_all_for_user = AsyncMock()

    async def _run():
        with patch.object(auth_mod, "SessionRepository", return_value=sessions_repo), patch.object(
            auth_mod, "UserRepository", return_value=MagicMock()
        ), patch.object(auth_mod, "OtpRepository", return_value=MagicMock()):
            svc = auth_mod.AuthService(db)
            await svc.logout(99, refresh_token=token)

    asyncio.run(_run())
    sessions_repo.revoke.assert_awaited_with(7)
    sessions_repo.revoke_all_for_user.assert_not_awaited()


def test_logout_without_refresh_token_revokes_all():
    from app.services import auth_service as auth_mod

    db = MagicMock(commit=AsyncMock())
    sessions_repo = MagicMock()
    sessions_repo.revoke_all_for_user = AsyncMock()

    async def _run():
        with patch.object(auth_mod, "SessionRepository", return_value=sessions_repo), patch.object(
            auth_mod, "UserRepository", return_value=MagicMock()
        ), patch.object(auth_mod, "OtpRepository", return_value=MagicMock()):
            svc = auth_mod.AuthService(db)
            await svc.logout(123)

    asyncio.run(_run())
    sessions_repo.revoke_all_for_user.assert_awaited_with(123)
