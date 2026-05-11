package com.tulip.common.core.error;

/**
 * 모든 도메인 에러 코드가 구현해야 하는 표준 계약.
 *
 * <p>코드 형식: {@code TLP-{DOMAIN}-{HTTP}-{SEQ}} (예: TLP-CMN-400-0001).
 * 형식 정의는 {@code 04_error_codes.md} §2 를 따른다.</p>
 */
public interface ErrorCode {

    /** {@code TLP-XXX-NNN-NNNN} 형식의 불변 코드 문자열. */
    String code();

    /** HTTP 응답 상태 코드. */
    int httpStatus();

    /** i18n 메시지 키 (예: {@code error.cmn.validation.required}). */
    String messageKey();

    /** 시스템(사서·관리자) 대상 기본 메시지. */
    String defaultMessage();

    /** OPAC 등 일반 이용자 대상 친화 메시지. null 가능. */
    default String defaultUserMessage() {
        return null;
    }
}
