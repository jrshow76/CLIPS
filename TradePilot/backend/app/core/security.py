"""보안 유틸: JWT 발급/검증, 비밀번호 해싱, OTP 생성/검증.

- JWT: HS256, access 30분 / refresh 7일.
- 비밀번호: bcrypt cost=12.
- OTP: 6자리 숫자, HMAC-SHA256으로 해시 저장, 5분 만료, 5회 시도 제한.
- AES-256-GCM: 계좌 비밀번호 등 민감 문자열 암호화 (Windows DPAPI 대신 Linux 환경).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AppException

# bcrypt 컨텍스트 (cost=12)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ---------------------------------------------------------------------------
# 비밀번호
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    """평문 비밀번호 → bcrypt 해시."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """평문 ↔ 해시 일치 여부."""
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


def password_policy_ok(password: str) -> tuple[bool, list[str]]:
    """비밀번호 정책 검증.

    8~32자, 영문/숫자/특수문자 각 1개 이상.
    반환: (통과여부, 위반사유 리스트)
    """
    errors: list[str] = []
    if not (8 <= len(password) <= 32):
        errors.append("8자 이상 32자 이하여야 합니다.")
    if not any(c.isalpha() for c in password):
        errors.append("영문자를 포함해야 합니다.")
    if not any(c.isdigit() for c in password):
        errors.append("숫자를 포함해야 합니다.")
    if not any(not c.isalnum() for c in password):
        errors.append("특수문자를 포함해야 합니다.")
    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
TokenType = Literal["access", "refresh"]


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_jwt_token(
    subject: str,
    token_type: TokenType,
    role: str = "ROLE_TRADER",
    trade_mode: str = "SIM",
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, int]:
    """JWT 발급.

    반환: (token, expires_in_sec)
    """
    if token_type == "access":
        ttl = settings.JWT_ACCESS_TTL_SEC
    else:
        ttl = settings.JWT_REFRESH_TTL_SEC

    now = _now_utc()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "role": role,
        "trade_mode": trade_mode,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "jti": uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, ttl


_ALLOWED_JWT_ALGORITHMS = ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512")


def decode_jwt_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """JWT 디코딩 + 검증.

    보안 강화:
    - ``alg=none`` 명시적 차단(허용 알고리즘 화이트리스트만 통과).
    - 토큰 헤더의 ``alg`` 값과 서버 설정 알고리즘 불일치 시 즉시 거절.
    - ``exp/iat/sub/type`` 클레임 누락 시 거절.

    실패 시 AppException(E0001 또는 E0053) 발생.
    """
    server_alg = settings.JWT_ALGORITHM
    if server_alg not in _ALLOWED_JWT_ALGORITHMS:
        # 설정 단계의 미스컨피그(예: 'none')는 즉시 인증 실패 처리
        raise AppException(
            "E0001",
            message="허용되지 않은 JWT 알고리즘 설정입니다.",
        )

    # alg 변조(alg=none, alg=HS256 강제 등) 방어: 서버 알고리즘과 정확히 일치만 허용
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise AppException("E0001", message="JWT 헤더 파싱 실패") from e

    token_alg = unverified_header.get("alg")
    if token_alg != server_alg or token_alg == "none":
        raise AppException(
            "E0001",
            message="JWT 알고리즘이 서버 정책과 일치하지 않습니다.",
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[server_alg],  # 단일 알고리즘만 허용
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise AppException("E0053", message="토큰이 만료되었습니다.") from e
    except jwt.PyJWTError as e:
        raise AppException("E0001", message="인증이 필요합니다.") from e

    if expected_type and payload.get("type") != expected_type:
        raise AppException("E0001", message=f"{expected_type} 토큰이 필요합니다.")
    return payload


def hash_refresh_token(token: str) -> str:
    """refresh_token을 DB에 저장할 SHA-256 해시로 변환."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------
def generate_otp_code(length: int | None = None) -> str:
    """랜덤 숫자 OTP 코드 생성 (기본 6자리)."""
    n = length or settings.OTP_LENGTH
    # 0~9 숫자 n개
    return "".join(str(secrets.randbelow(10)) for _ in range(n))


def hash_otp_code(code: str, salt: str = "") -> str:
    """OTP 코드를 HMAC-SHA256으로 해시 (DB 저장용)."""
    key = (settings.JWT_SECRET + salt).encode("utf-8")
    return hmac.new(key, code.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_otp_code(plain_code: str, hashed: str, salt: str = "") -> bool:
    """OTP 검증 (timing-safe 비교)."""
    return hmac.compare_digest(hash_otp_code(plain_code, salt), hashed)


# ---------------------------------------------------------------------------
# AES-256-GCM (계좌 비밀번호 등)
# ---------------------------------------------------------------------------
def _aes_key_bytes() -> bytes:
    """AES_KEY를 32바이트로 정규화. base64 디코딩 실패 시 SHA-256 파생."""
    raw = settings.AES_KEY
    try:
        decoded = base64.b64decode(raw, validate=True)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    return hashlib.sha256(raw.encode("utf-8")).digest()


def aes_encrypt(plaintext: str) -> str:
    """AES-256-GCM 암호화. nonce + ciphertext+tag를 base64로 직렬화."""
    aesgcm = AESGCM(_aes_key_bytes())
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def aes_decrypt(token: str) -> str:
    """AES-256-GCM 복호화."""
    aesgcm = AESGCM(_aes_key_bytes())
    raw = base64.b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
