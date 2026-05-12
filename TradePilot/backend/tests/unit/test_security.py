"""security 모듈 단위 테스트."""
from __future__ import annotations

import pytest

from app.core.security import (
    aes_decrypt,
    aes_encrypt,
    create_jwt_token,
    decode_jwt_token,
    generate_otp_code,
    hash_otp_code,
    hash_password,
    password_policy_ok,
    verify_otp_code,
    verify_password,
)


class TestPassword:
    @pytest.mark.unit
    def test_hash_and_verify(self) -> None:
        h = hash_password("S3cure!Pass")
        assert verify_password("S3cure!Pass", h)
        assert not verify_password("wrong", h)

    @pytest.mark.unit
    def test_policy_ok(self) -> None:
        ok, errors = password_policy_ok("Abcd1234!")
        assert ok
        assert errors == []

    @pytest.mark.unit
    def test_policy_violation(self) -> None:
        ok, errors = password_policy_ok("short")
        assert not ok
        assert len(errors) >= 2


class TestJWT:
    @pytest.mark.unit
    def test_create_and_decode(self) -> None:
        token, ttl = create_jwt_token(
            subject="user-uuid", token_type="access", role="ROLE_TRADER"
        )
        assert ttl > 0
        payload = decode_jwt_token(token, expected_type="access")
        assert payload["sub"] == "user-uuid"
        assert payload["role"] == "ROLE_TRADER"

    @pytest.mark.unit
    def test_wrong_type_rejected(self) -> None:
        token, _ = create_jwt_token(subject="x", token_type="refresh")
        from app.core.exceptions import AppException

        with pytest.raises(AppException) as exc_info:
            decode_jwt_token(token, expected_type="access")
        assert exc_info.value.code == "E0001"


class TestOTP:
    @pytest.mark.unit
    def test_otp_roundtrip(self) -> None:
        code = generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()
        h = hash_otp_code(code)
        assert verify_otp_code(code, h)
        assert not verify_otp_code("000000" if code != "000000" else "111111", h)


class TestAES:
    @pytest.mark.unit
    def test_encrypt_decrypt_roundtrip(self) -> None:
        secret = "비밀번호12345!"
        token = aes_encrypt(secret)
        assert token != secret
        assert aes_decrypt(token) == secret
