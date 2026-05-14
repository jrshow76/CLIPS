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
    create_refresh_token_with_jti,
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
        # SEC-004(GATE-3): refresh 토큰은 jti와 함께 발급하여 DB와 동기화한다.
        refresh, refresh_jti, refresh_ttl = create_refresh_token_with_jti(
            subject=str(user.public_id),
            role=user.role,
            trade_mode=user.trade_mode,
        )

        # 세션 저장 (jti + issued_at 포함)
        issued = datetime.now(tz=timezone.utc)
        from uuid import UUID as _UUID

        sess = Session(
            user_id=user.id,
            jti=_UUID(refresh_jti),
            refresh_token_hash=hash_refresh_token(refresh),
            user_agent=(user_agent or "")[:255] or None,
            ip_address=ip,
            issued_at=issued,
            expires_at=issued + timedelta(seconds=refresh_ttl),
        )
        await self.sessions.add(sess)
        await self.db.commit()
        log.info("user_login", user_id=user.id, email=email)
        return user, access, refresh, access_ttl

    # ------------------------------------------------------------------
    # Refresh (SEC-004 GATE-3: 완전 Token Rotation)
    # ------------------------------------------------------------------
    async def refresh(
        self, refresh_token: str, user_agent: str | None = None, ip: str | None = None
    ) -> tuple[str, str, int, int]:
        """Refresh 토큰 회전 + Access 재발급.

        SEC-004(GATE-3) 완전 해소:
        1. JWT 디코딩 → ``jti`` 클레임 추출.
        2. DB에서 jti 조회.
           - 미존재(legacy or 위조): 토큰 hash로 재시도 (마이그레이션 호환). 그래도 없으면 사용자 전 세션 폐기.
           - 존재하지만 ``revoked_at IS NOT NULL``: **REPLAY 탐지** → 사용자 전 refresh 세션 일괄 폐기 +
             Redis 보안 이벤트 publish (``tp:security.events``).
           - 만료된 경우: E0053.
        3. 정상 경로: 새 jti + 새 refresh + 새 access 발급. 기존 세션은 ``revoked_at + replaced_by_jti`` 갱신.
        4. 클라이언트는 새 refresh 토큰을 보관하여 다음 회전에 사용.

        반환: (access_token, new_refresh_token, access_ttl_sec, refresh_ttl_sec)
        """
        from datetime import datetime, timezone
        from uuid import UUID as _UUID

        from app.core.security import decode_jwt_token

        payload = decode_jwt_token(refresh_token, expected_type="refresh")
        public_id = payload.get("sub")
        token_jti = payload.get("jti")

        # 1) jti 기반 조회 (폐기/만료 무관)
        sess: Session | None = None
        if token_jti:
            sess = await self.sessions.find_by_jti(token_jti)

        # 1-a) jti가 미존재면 hash 기반 fallback (legacy 세션 호환).
        if sess is None:
            token_hash = hash_refresh_token(refresh_token)
            from sqlalchemy import select as _select

            stmt = _select(Session).where(Session.refresh_token_hash == token_hash).limit(1)
            sess = (await self.db.execute(stmt)).scalar_one_or_none()

        # 2) 세션 자체가 존재하지 않음 = 위조/legacy 만료 → 사용자 전 세션 폐기
        if sess is None:
            if public_id:
                user = await self.users.find_by_public_id(public_id)
                if user:
                    log.warning(
                        "refresh_token_unknown",
                        user_id=user.id,
                        public_id=public_id,
                        jti=token_jti,
                    )
                    await self.sessions.revoke_all_for_user(user.id)
                    await self._publish_security_event(
                        event_type="refresh_token_unknown",
                        user_id=user.id,
                        public_id=str(public_id),
                        jti=token_jti,
                    )
                    await self.db.commit()
            raise AppException("E0001", message="유효하지 않은 리프레시 토큰입니다.")

        # 3) 이미 폐기된 jti가 다시 들어옴 = REPLAY 탐지
        if sess.revoked_at is not None:
            log.warning(
                "refresh_token_replay_detected",
                user_id=sess.user_id,
                session_id=sess.id,
                jti=token_jti,
            )
            await self.sessions.revoke_all_for_user(sess.user_id)
            await self._publish_security_event(
                event_type="refresh_replay_detected",
                user_id=sess.user_id,
                public_id=str(public_id) if public_id else None,
                jti=token_jti,
            )
            # 보안 이벤트 알림 (이메일/카카오/SMS) — 실패해도 인증 흐름 차단 금지
            try:
                from app.services.notification_service import NotificationService

                victim = await self.users.get(sess.user_id)
                if victim is not None:
                    await NotificationService(self.db).send_security_alert(
                        user=victim,
                        event_type_code="refresh_replay_detected",
                        ip=ip,
                        user_agent=user_agent,
                        detail="동일 리프레시 토큰이 두 번 이상 사용되어 모든 세션이 폐기되었습니다.",
                    )
            except Exception as _e:  # noqa: BLE001
                log.warning("security_notify_failed", user_id=sess.user_id, error=str(_e)[:200])
            await self.db.commit()
            raise AppException("E0001", message="리프레시 토큰 재사용이 감지되었습니다. 다시 로그인해주세요.")

        # 4) 만료 검증
        if sess.expires_at and sess.expires_at < datetime.now(tz=timezone.utc):
            raise AppException("E0053", message="세션이 만료되었습니다.")

        user = await self.users.find_by_public_id(public_id)
        if not user:
            raise AppException("E0001")

        # 5) 새 refresh + access 발급 (회전)
        new_refresh, new_jti, new_refresh_ttl = create_refresh_token_with_jti(
            subject=str(user.public_id),
            role=user.role,
            trade_mode=user.trade_mode,
        )
        access, access_ttl = create_jwt_token(
            subject=str(user.public_id),
            token_type="access",
            role=user.role,
            trade_mode=user.trade_mode,
        )

        now = datetime.now(tz=timezone.utc)
        new_sess = Session(
            user_id=user.id,
            jti=_UUID(new_jti),
            refresh_token_hash=hash_refresh_token(new_refresh),
            user_agent=(user_agent or sess.user_agent or "")[:255] or None,
            ip_address=ip or (str(sess.ip_address) if sess.ip_address else None),
            device_id=sess.device_id,
            issued_at=now,
            expires_at=now + timedelta(seconds=new_refresh_ttl),
        )
        await self.sessions.add(new_sess)
        # 기존 세션 즉시 폐기 + 회전 체인 기록
        await self.sessions.rotate(sess, new_jti)
        await self.db.commit()

        log.info(
            "refresh_token_rotated",
            user_id=user.id,
            old_jti=str(sess.jti) if sess.jti else None,
            new_jti=new_jti,
        )
        return access, new_refresh, access_ttl, new_refresh_ttl

    async def _publish_security_event(
        self,
        *,
        event_type: str,
        user_id: int | None,
        public_id: str | None = None,
        jti: str | None = None,
    ) -> None:
        """보안 이벤트를 Redis ``tp:security.events`` 채널에 publish.

        실패는 로그만 남기고 무시한다(인증 흐름 차단 방지).
        """
        try:
            payload = {
                "type": event_type,
                "user_id": user_id,
                "public_id": public_id,
                "jti": jti,
                "ts": datetime.now(tz=timezone.utc).isoformat(),
            }
            await get_redis().publish("tp:security.events", orjson.dumps(payload))
        except Exception as e:
            log.warning("security_event_publish_failed", event_type=event_type, error=str(e))

    # ------------------------------------------------------------------
    # 로그아웃
    # ------------------------------------------------------------------
    async def logout(self, user_id: int, refresh_token: str | None = None) -> None:
        """로그아웃.

        SEC-004(GATE-3): refresh 토큰이 함께 전달되면 해당 jti만 폐기한다.
        토큰이 없으면 사용자의 모든 활성 세션 폐기(기존 동작 유지).
        """
        if refresh_token:
            from app.core.security import decode_jwt_token

            try:
                payload = decode_jwt_token(refresh_token, expected_type="refresh")
                jti = payload.get("jti")
                if jti:
                    sess = await self.sessions.find_by_jti(jti)
                    if sess and sess.revoked_at is None and sess.user_id == user_id:
                        await self.sessions.revoke(sess.id)
                        await self.db.commit()
                        log.info("user_logout_session", user_id=user_id, jti=jti)
                        return
            except AppException:
                # 토큰 손상/만료여도 user_id 기반 일괄 폐기로 fallback
                pass
        await self.sessions.revoke_all_for_user(user_id)
        await self.db.commit()
        log.info("user_logout_all", user_id=user_id)

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
