package com.tulip.iam.mfa;

/**
 * TOTP(MFA) 서비스 인터페이스 골격 (Sprint 1-B.8).
 *
 * <p>{@code 05_security_and_auth.md} §5.2 — PLATFORM_ADMIN/TENANT_ADMIN 필수, DIRECTOR/LIBRARIAN_HEAD 권장.
 * Phase 2 에서 RFC 6238 TOTP + 백업 코드 구현 예정. Phase 1-B 는 인터페이스와 컨트롤러 스텁만 둔다.</p>
 */
public interface TotpService {

    /** TOTP 시크릿을 발급하고 QR 코드용 otpauth URL 을 반환한다. */
    SetupResult setupSecret(String userId);

    /** 사용자가 입력한 TOTP 코드 검증. */
    boolean verify(String userId, String code);

    /** 등록 결과. */
    record SetupResult(String secretBase32, String otpAuthUrl) {
    }
}
