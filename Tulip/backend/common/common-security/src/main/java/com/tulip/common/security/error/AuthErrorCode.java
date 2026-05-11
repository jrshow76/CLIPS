package com.tulip.common.security.error;

import com.tulip.common.core.error.ErrorCode;

/**
 * 인증·인가 도메인(AUT) 표준 에러 코드.
 *
 * <p>{@code 04_error_codes.md} §5.1 의 TLP-AUT-* 코드를 enum 으로 발급한다.
 * IAM 서비스·Gateway·각 서비스 보안 핸들러 공통으로 사용된다.</p>
 *
 * <p>표(5.1)에 등재된 코드만 본 enum 에 등록한다. 신규 코드 발급은 DevLead 승인 절차를 따른다.</p>
 */
public enum AuthErrorCode implements ErrorCode {

    // ---------------- 401 미인증 ----------------
    TOKEN_MISSING("TLP-AUT-401-0001", 401,
            "error.aut.token.missing", "인증 토큰이 없습니다",
            "로그인이 필요합니다."),
    TOKEN_EXPIRED("TLP-AUT-401-0002", 401,
            "error.aut.token.expired", "인증 토큰이 만료되었습니다",
            "다시 로그인해 주세요."),
    TOKEN_INVALID("TLP-AUT-401-0003", 401,
            "error.aut.token.invalid", "유효하지 않은 토큰입니다",
            "다시 로그인해 주세요."),
    LOGIN_FAILED("TLP-AUT-401-0004", 401,
            "error.aut.login.failed", "아이디 또는 비밀번호가 일치하지 않습니다",
            "아이디 또는 비밀번호를 확인해 주세요."),
    MFA_REQUIRED("TLP-AUT-401-0005", 401,
            "error.aut.mfa.required", "추가 인증(MFA)이 필요합니다",
            "추가 인증을 완료해 주세요."),
    MFA_INVALID("TLP-AUT-401-0006", 401,
            "error.aut.mfa.invalid", "MFA 코드가 일치하지 않습니다",
            "MFA 코드를 다시 입력해 주세요."),
    SSO_FAILED("TLP-AUT-401-0007", 401,
            "error.aut.sso.failed", "외부 인증(SSO) 실패",
            "외부 인증을 다시 시도해 주세요."),

    // ---------------- 403 권한 ----------------
    PERMISSION_DENIED("TLP-AUT-403-0001", 403,
            "error.aut.permission.denied", "권한이 없습니다",
            "해당 작업을 수행할 권한이 없습니다."),
    TENANT_MISMATCH("TLP-AUT-403-0002", 403,
            "error.aut.tenant.mismatch", "다른 테넌트의 자원입니다",
            "접근할 수 없는 자원입니다."),
    BRANCH_MISMATCH("TLP-AUT-403-0003", 403,
            "error.aut.branch.mismatch", "해당 관에 권한이 없습니다",
            "해당 도서관에 접근 권한이 없습니다."),
    ROLE_INSUFFICIENT("TLP-AUT-403-0004", 403,
            "error.aut.role.insufficient", "필요한 역할이 없습니다",
            "해당 작업을 수행할 역할이 없습니다."),
    SCOPE_INSUFFICIENT("TLP-AUT-403-0005", 403,
            "error.aut.scope.insufficient", "토큰 scope 가 부족합니다",
            "재로그인 후 다시 시도해 주세요."),

    // ---------------- 423 잠금 ----------------
    ACCOUNT_LOCKED("TLP-AUT-423-0001", 423,
            "error.aut.account.locked", "계정이 잠겨있습니다",
            "관리자에게 문의해 주세요."),

    // ---------------- 429 Rate Limit ----------------
    LOGIN_TOO_MANY("TLP-AUT-429-0001", 429,
            "error.aut.login.too_many", "로그인 시도가 너무 많습니다",
            "잠시 후 다시 시도해 주세요."),

    // ---------------- 500 시스템 ----------------
    JWKS_FETCH_FAILED("TLP-AUT-500-0001", 500,
            "error.aut.jwks.fetch_failed", "JWKS 조회에 실패했습니다",
            "잠시 후 다시 시도해 주세요.");

    private final String code;
    private final int httpStatus;
    private final String messageKey;
    private final String defaultMessage;
    private final String defaultUserMessage;

    AuthErrorCode(String code, int httpStatus, String messageKey,
                  String defaultMessage, String defaultUserMessage) {
        this.code = code;
        this.httpStatus = httpStatus;
        this.messageKey = messageKey;
        this.defaultMessage = defaultMessage;
        this.defaultUserMessage = defaultUserMessage;
    }

    @Override public String code() { return code; }
    @Override public int httpStatus() { return httpStatus; }
    @Override public String messageKey() { return messageKey; }
    @Override public String defaultMessage() { return defaultMessage; }
    @Override public String defaultUserMessage() { return defaultUserMessage; }
}
