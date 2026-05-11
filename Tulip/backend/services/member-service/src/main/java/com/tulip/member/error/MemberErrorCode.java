package com.tulip.member.error;

import com.tulip.common.core.error.ErrorCode;

/**
 * member-service 도메인 에러 코드.
 *
 * <p>코드 형식은 {@code 04_error_codes.md} §2 에 따른 {@code TLP-MBR-{HTTP}-{SEQ}} 형식이다.
 * 회원 도메인은 표준 표(5.2 CMN)에 일부 정의되어 있으나, member-service 가 자체적으로
 * 명시 발급해야 하는 경우 본 enum 을 사용한다.</p>
 *
 * <p>표 5.2 의 CMN 코드가 이미 적용 가능한 경우(예: CMN-404-0002 회원 미존재)는 가급적
 * 공통 {@code CommonErrorCode} 를 그대로 활용하고, 회원 카드·동의 등 MBR 고유 도메인은
 * 본 enum 에서 신규 발급한다.</p>
 */
public enum MemberErrorCode implements ErrorCode {

    // ----------------- 400 입력 검증 -----------------
    MEMBER_INVALID_PHONE("TLP-MBR-400-0001", 400,
            "error.mbr.member.invalid_phone", "전화번호 형식이 올바르지 않습니다"),
    MEMBER_INVALID_EMAIL("TLP-MBR-400-0002", 400,
            "error.mbr.member.invalid_email", "이메일 형식이 올바르지 않습니다"),
    MEMBER_INVALID_BIRTHDATE("TLP-MBR-400-0003", 400,
            "error.mbr.member.invalid_birthdate", "생년월일이 유효하지 않습니다"),
    CARD_INVALID_EXPIRY("TLP-MBR-400-0004", 400,
            "error.mbr.card.invalid_expiry", "회원증 만료일이 유효하지 않습니다"),

    // ----------------- 403 권한 -----------------
    MEMBER_FORBIDDEN_SELF("TLP-MBR-403-0001", 403,
            "error.mbr.member.forbidden_self", "본인 정보가 아니어서 접근할 수 없습니다",
            "본인 정보만 조회/수정할 수 있습니다."),

    // ----------------- 404 자원 -----------------
    MEMBER_NOT_FOUND("TLP-MBR-404-0001", 404,
            "error.mbr.member.not_found", "회원을 찾을 수 없습니다"),
    CARD_NOT_FOUND("TLP-MBR-404-0002", 404,
            "error.mbr.card.not_found", "회원증을 찾을 수 없습니다"),
    CONSENT_NOT_FOUND("TLP-MBR-404-0003", 404,
            "error.mbr.consent.not_found", "동의 이력을 찾을 수 없습니다"),

    // ----------------- 409 충돌 -----------------
    MEMBER_NO_DUPLICATE("TLP-MBR-409-0001", 409,
            "error.mbr.member.no_duplicate", "이미 사용 중인 회원번호입니다"),
    MEMBER_EMAIL_DUPLICATE("TLP-MBR-409-0002", 409,
            "error.mbr.member.email_duplicate", "이미 등록된 이메일입니다"),
    MEMBER_ALREADY_DELETED("TLP-MBR-409-0003", 409,
            "error.mbr.member.already_deleted", "이미 삭제된 회원입니다"),
    CARD_ALREADY_ISSUED("TLP-MBR-409-0004", 409,
            "error.mbr.card.already_issued", "현재 사용 중인 회원증이 이미 있습니다"),

    // ----------------- 422 비즈니스 -----------------
    CONSENT_REQUIRED("TLP-MBR-422-0001", 422,
            "error.mbr.consent.required", "필수 동의 항목을 누락했습니다",
            "개인정보 처리 동의가 필요합니다."),
    MEMBER_SUSPENDED("TLP-MBR-422-0002", 422,
            "error.mbr.member.suspended", "이용 제한 상태입니다"),
    CARD_STATE_INVALID("TLP-MBR-422-0003", 422,
            "error.mbr.card.state_invalid", "현재 상태에서는 카드 작업을 수행할 수 없습니다"),

    // ----------------- 500 시스템 -----------------
    MEMBER_PII_DECRYPT_FAILED("TLP-MBR-500-0001", 500,
            "error.mbr.pii.decrypt_failed", "개인정보 복호화에 실패했습니다");

    private final String code;
    private final int httpStatus;
    private final String messageKey;
    private final String defaultMessage;
    private final String defaultUserMessage;

    MemberErrorCode(String code, int httpStatus, String messageKey, String defaultMessage) {
        this(code, httpStatus, messageKey, defaultMessage, null);
    }

    MemberErrorCode(String code, int httpStatus, String messageKey,
                    String defaultMessage, String defaultUserMessage) {
        this.code = code;
        this.httpStatus = httpStatus;
        this.messageKey = messageKey;
        this.defaultMessage = defaultMessage;
        this.defaultUserMessage = defaultUserMessage;
    }

    @Override
    public String code() {
        return code;
    }

    @Override
    public int httpStatus() {
        return httpStatus;
    }

    @Override
    public String messageKey() {
        return messageKey;
    }

    @Override
    public String defaultMessage() {
        return defaultMessage;
    }

    @Override
    public String defaultUserMessage() {
        return defaultUserMessage;
    }
}
