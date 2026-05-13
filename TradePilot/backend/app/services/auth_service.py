"""인증 서비스 (유스케이스).

회원가입/로그인/리프레시/로그아웃/OTP 발급·검증/비밀번호 변경·재설정을 처리한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import orjson
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.redis_client import get_redis
from app.core.security import (
    create_jwt_token,
    generate_otp_code,
    hash_otp_code,
    hash_password,
    hash_refresh_token,
    password_policy_ok,
    verify_otp_code,
    verify_password,
)
from app.models.user import OtpCode, Session, User, UserSettings
from app.repositories.user_repository import (
    OtpRepository,
    SessionRepository,
    UserRepository,
)

log = structlog.get_logger(__name__)

# 계정 잠금 정책
MAX_LOGIN_FAILS = 5
LOCK_DURATION_MIN = 15


class AuthService:
    """인증 도메인 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.otps = OtpRepository(db)
        self.sessions = SessionRepository(db)

    # ------------------------------------------------------------------
    # 회원가입
    # ------------------------------------------------------------------
    async def signup(self, email: str, password: str, nickname: str) -> User:
        # 비밀번호 정책
        ok, errors = password_policy_ok(password)
        if not ok:
            raise AppException(
                "E0055",
                message="비밀번호 정책에 위반됩니다.",
                details={"password": errors},
            )

        # 이메일 중복 확인
        existing = await self.users.find_by_email(email)
        if existing:
            raise AppException("E0051", message="이미 가입된 이메일입니다.")

        user = User(
            email=email,
            password_hash=hash_password(password),
            nickname=nickname,
            role="ROLE_TRADER",
            trade_mode="SIM",
        )
        await self.users.add(user)
        # 기본 설정 동시 생성
        self.db.add(UserSettings(user_id=user.id))
        await self.db.commit()
        await self.db.refresh(user)
        log.info("user_signup", user_id=user.id, email=email)
        return user

    # ------------------------------------------------------------------
    # 로그인
    # ------------------------------------------------------------------
    async def login(
        self, email: str, password: str, user_agent: str | None = None, ip: str | None = None
    ) -> tuple[User, str, str, int]:
        """반환: (user, access_token, refresh_token, expires_in)"""
        user = await self.users.find_by_email(email)
        if not user:
            raise AppException("E0001", message="이메일 또는 비밀번호가 올바르지 않습니다.")

        # 계정 잠금 확인
        now = datetime.now(tz=timezone.utc)
        if user.locked_until and user.locked_until > now:
            raise AppException("E0052", message="계정이 잠겨있습니다. 잠시 후 다시 시도해주세요.")

        if not verify_password(password, user.password_hash):
            lock_until = None
            if user.login_fail_count + 1 >= MAX_LOGIN_FAILS:
                lock_until = now + timedelta(minutes=LOCK_DURATION_MIN)
            await self.users.increment_login_fail(user.id, lock_until)
            await self.db.commit()
            if lock_until:
                raise AppException(
                    "E0052",
                    message=f"로그인 실패가 누적되어 {LOCK_DURATION_MIN}분간 계정이 잠겼습니다.",
                )
            raise AppException("E0001", message="이메일 또는 비밀번호가 올바르지 않습니다.")

        # 성공 처리
        await self.users.reset_login_fail(user.id)

        access, access_ttl = create_jwt_token(
            subject=str(user.public_id),
            token_type="access",
            role=user.role,
            trade_mode=user.trade_mode,
        )
        refresh, refresh_ttl = create_jwt_token(
            subject=str(user.public_id),
            token_type="refresh",
            role=user.role,
            trade_mode=user.trade_mode,
        )

        # 세션 저장
        sess = Session(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh),
            user_agent=(user_agent or "")[:255] or None,
            ip_address=ip,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(seconds=refresh_ttl),
        )
        await self.sessions.add(sess)
        await self.db.commit()
        log.info("user_login", user_id=user.id, email=email)
        return user, access, refresh, access_ttl

    # ------------------------------------------------------------------
    # Refresh (SEC-006: Token Rotation)
    # ------------------------------------------------------------------
    async def refresh(self, refresh_token: str) -> tuple[str, int]:
        """Access 토큰 재발급.

        SEC-006 보강:
        - 동일 refresh_token이 재사용되면(이미 회수된 세션) 모든 세션 일괄 폐기.
          → refresh token replay 공격(탈취 토큰 재사용) 탐지 시 강제 로그아웃.
        - 본 메서드 자체는 access 토큰만 발급한다. refresh 토큰 자체의 회전은
          상위 라우터에서 새 세션을 발급하는 식으로 확장 가능.
        """
        from app.core.security import decode_jwt_token

        payload = decode_jwt_token(refresh_token, expected_type="refresh")
        public_id = payload.get("sub")

        token_hash = hash_refresh_token(refresh_token)
        sess = await self.sessions.find_by_hash(token_hash)
        if not sess:
            # 폐기된 토큰이 다시 사용됨 = 탈취 의심. user_id를 알 수 있으면 전 세션 폐기.
            if public_id:
                user = await self.users.find_by_public_id(public_id)
                if user:
                    log.warning(
                        "refresh_token_replay_detected",
                        user_id=user.id,
                        public_id=public_id,
                    )
                    await self.sessions.revoke_all_for_user(user.id)
                    await self.db.commit()
            raise AppException("E0001", message="유효하지 않은 리프레시 토큰입니다.")

        # 만료 검증
        from datetime import datetime, timezone
        if sess.expires_at and sess.expires_at < datetime.now(tz=timezone.utc):
            raise AppException("E0053", message="세션이 만료되었습니다.")

        user = await self.users.find_by_public_id(public_id)
        if not user:
            raise AppException("E0001")

        access, ttl = create_jwt_token(
            subject=str(user.public_id),
            token_type="access",
            role=user.role,
            trade_mode=user.trade_mode,
        )
        return access, ttl

    # ------------------------------------------------------------------
    # 로그아웃
    # ------------------------------------------------------------------
    async def logout(self, user_id: int) -> None:
        await self.sessions.revoke_all_for_user(user_id)
        await self.db.commit()

    # ------------------------------------------------------------------
    # OTP
    # ------------------------------------------------------------------
    async def send_otp(
        self,
        *,
        user_id: int,
        purpose: str,
        channel: str,
        phone: str | None = None,
    ) -> tuple[str, int]:
        """OTP 발급. 반환: (otp_id_uuid, ttl_sec)

        v1.0은 SMS/EMAIL 실제 발송 대신 로그로만 출력한다 (개발/테스트).
        운영 환경에서는 NotificationService 와 연동 예정.
        """
        code = generate_otp_code()
        code_hash = hash_otp_code(code)
        otp_id = uuid4()
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=settings.OTP_TTL_SEC)

        otp = await self.otps.create(
            user_id=user_id,
            otp_id=otp_id,
            purpose=purpose,
            code_hash=code_hash,
            channel=channel,
            expires_at=expires_at,
        )
        await self.db.commit()

        # 발송 (운영: NotificationService 연동 예정)
        # SEC-009: OTP 평문은 로그에 절대 남기지 않는다(디버그 환경 포함).
        # 개발 편의용 평문 보관은 Redis 키(otp:debug:*)를 통해서만 제공하며,
        # 본 키는 운영 환경에서 절대 사용하지 않는다.
        log.info(
            "otp_generated",
            user_id=user_id,
            otp_id=str(otp_id),
            purpose=purpose,
            channel=channel,
        )
        if settings.is_dev or settings.is_test:
            await get_redis().setex(f"otp:debug:{otp_id}", settings.OTP_TTL_SEC, code)
        return str(otp_id), settings.OTP_TTL_SEC

    async def verify_otp(self, otp_id_str: str, plain_code: str) -> str:
        """OTP 검증. 성공 시 단기 검증 토큰(JWT) 반환."""
        from uuid import UUID

        try:
            otp_uuid = UUID(otp_id_str)
        except ValueError as e:
            raise AppException("E0003", message="otp_id 형식 오류") from e

        otp: OtpCode | None = await self.otps.find_active(otp_uuid)
        if not otp:
            raise AppException("E0053", message="OTP가 만료되었거나 존재하지 않습니다.")

        if otp.expires_at < datetime.now(tz=timezone.utc):
            raise AppException("E0053", message="OTP가 만료되었습니다.")

        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            raise AppException("E0011", message="OTP 시도 횟수를 초과했습니다.")

        if not verify_otp_code(plain_code, otp.code_hash):
            await self.otps.increment_attempt(otp.id)
            await self.db.commit()
            raise AppException("E0011", message="OTP가 올바르지 않습니다.")

        await self.otps.consume(otp.id)
        await self.db.commit()

        # 단기 토큰 발급 (10분)
        token, _ = create_jwt_token(
            subject=str(otp.user_id),
            token_type="access",
            role="ROLE_OTP",
            trade_mode="SIM",
            extra_claims={"otp_purpose": otp.purpose, "exp_short": True},
        )
        return token

    # ------------------------------------------------------------------
    # 비밀번호 변경/재설정
    # ------------------------------------------------------------------
    async def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> None:
        user = await self.users.get(user_id)
        if not user or not verify_password(current_password, user.password_hash):
            raise AppException("E0001", message="현재 비밀번호가 올바르지 않습니다.")

        ok, errors = password_policy_ok(new_password)
        if not ok:
            raise AppException("E0055", details={"new_password": errors})

        await self.users.update_password(user_id, hash_password(new_password))
        await self.sessions.revoke_all_for_user(user_id)  # 세션 무효화
        await self.db.commit()
        log.info("password_changed", user_id=user_id)

    async def request_password_reset(self, email: str) -> None:
        """비밀번호 재설정 토큰 발급. 실제 메일 발송은 별도 서비스."""
        user = await self.users.find_by_email(email)
        if not user:
            # 보안상 존재 여부 비노출 - 성공으로 응답
            return
        token = uuid4().hex
        await get_redis().setex(
            f"pwreset:{token}",
            3600,
            orjson.dumps({"user_id": user.id, "email": email}),
        )
        # SEC-009: 토큰 평문은 로그에 남기지 않는다. 개발 환경 디버깅이 필요하면
        # Redis 키(pwreset:*)를 직접 조회하라.
        log.info("password_reset_token_issued", user_id=user.id)

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        raw = await get_redis().get(f"pwreset:{token}")
        if not raw:
            raise AppException("E0054", message="비밀번호 재설정 토큰이 유효하지 않습니다.")
        data = orjson.loads(raw)
        user_id = int(data["user_id"])

        ok, errors = password_policy_ok(new_password)
        if not ok:
            raise AppException("E0055", details={"new_password": errors})

        await self.users.update_password(user_id, hash_password(new_password))
        await self.sessions.revoke_all_for_user(user_id)
        await self.db.commit()
        await get_redis().delete(f"pwreset:{token}")
        log.info("password_reset_done", user_id=user_id)
