package com.tulip.tenant.error;

import com.tulip.common.core.error.ErrorCode;

/**
 * Tulip+ tenant-service 전용 도메인 에러 코드.
 *
 * <p>코드 형식: {@code TLP-TNT-{HTTP}-{SEQ}} — 04_error_codes.md §2 규약.
 * TNT 도메인은 공통 마스터(테넌트/라이브러리/분관/설정/Outbox) 한정으로 사용한다.</p>
 */
public enum TenantErrorCode implements ErrorCode {

    // ---------- 400 입력 검증 ----------
    TENANT_CODE_INVALID("TLP-TNT-400-0001", 400,
            "error.tnt.tenant.code.invalid", "테넌트 코드 형식이 올바르지 않습니다"),
    LIBRARY_CODE_INVALID("TLP-TNT-400-0002", 400,
            "error.tnt.library.code.invalid", "라이브러리 코드 형식이 올바르지 않습니다"),
    SETTING_KEY_INVALID("TLP-TNT-400-0003", 400,
            "error.tnt.setting.key.invalid", "설정 키 형식이 올바르지 않습니다(NAMESPACE.KEY)"),
    INVALID_STATUS_TRANSITION("TLP-TNT-400-0004", 400,
            "error.tnt.status.transition", "허용되지 않은 상태 전이입니다"),

    // ---------- 403 권한 ----------
    SYSTEM_ADMIN_REQUIRED("TLP-TNT-403-0001", 403,
            "error.tnt.sys_admin.required", "시스템 관리자 권한이 필요합니다"),
    TENANT_MISMATCH("TLP-TNT-403-0002", 403,
            "error.tnt.tenant.mismatch", "다른 테넌트의 자원에 접근할 수 없습니다"),

    // ---------- 404 자원 ----------
    TENANT_NOT_FOUND("TLP-TNT-404-0001", 404,
            "error.tnt.tenant.not_found", "테넌트를 찾을 수 없습니다"),
    LIBRARY_NOT_FOUND("TLP-TNT-404-0002", 404,
            "error.tnt.library.not_found", "라이브러리를 찾을 수 없습니다"),
    BRANCH_NOT_FOUND("TLP-TNT-404-0003", 404,
            "error.tnt.branch.not_found", "분관을 찾을 수 없습니다"),
    SETTING_NOT_FOUND("TLP-TNT-404-0004", 404,
            "error.tnt.setting.not_found", "테넌트 설정을 찾을 수 없습니다"),

    // ---------- 409 충돌 ----------
    TENANT_CODE_DUPLICATE("TLP-TNT-409-0001", 409,
            "error.tnt.tenant.code.duplicate", "이미 사용 중인 테넌트 코드입니다"),
    LIBRARY_CODE_DUPLICATE("TLP-TNT-409-0002", 409,
            "error.tnt.library.code.duplicate", "이미 사용 중인 라이브러리 코드입니다"),
    BRANCH_CODE_DUPLICATE("TLP-TNT-409-0003", 409,
            "error.tnt.branch.code.duplicate", "이미 사용 중인 분관 코드입니다"),
    TENANT_NOT_SUSPENDED("TLP-TNT-409-0004", 409,
            "error.tnt.tenant.not_suspended", "테넌트는 SUSPENDED 상태에서만 종료(삭제)할 수 있습니다"),

    // ---------- 422 비즈니스 ----------
    LIBRARY_HAS_ACTIVE_BRANCHES("TLP-TNT-422-0001", 422,
            "error.tnt.library.has_branches", "활성 분관이 남아 있어 라이브러리를 삭제할 수 없습니다"),

    // ---------- 500 시스템 ----------
    OUTBOX_PUBLISH_FAILED("TLP-TNT-500-0001", 500,
            "error.tnt.outbox.publish_failed", "이벤트 발행에 실패했습니다");

    private final String code;
    private final int httpStatus;
    private final String messageKey;
    private final String defaultMessage;

    TenantErrorCode(String code, int httpStatus, String messageKey, String defaultMessage) {
        this.code = code;
        this.httpStatus = httpStatus;
        this.messageKey = messageKey;
        this.defaultMessage = defaultMessage;
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
}
