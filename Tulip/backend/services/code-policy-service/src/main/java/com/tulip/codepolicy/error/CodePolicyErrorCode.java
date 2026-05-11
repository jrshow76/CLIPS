package com.tulip.codepolicy.error;

import com.tulip.common.core.error.ErrorCode;

/**
 * code-policy-service 도메인 에러 코드.
 *
 * <p>형식: {@code TLP-CDP-{HTTP}-{SEQ}} ({@code 04_error_codes.md} §2).</p>
 */
public enum CodePolicyErrorCode implements ErrorCode {

    // ----------------- 400 검증 -----------------
    CODE_INVALID_HIERARCHY("TLP-CDP-400-0001", 400,
            "error.cdp.code.invalid_hierarchy", "코드 계층 깊이가 허용 범위를 벗어났습니다"),
    POLICY_INVALID_RULES("TLP-CDP-400-0002", 400,
            "error.cdp.policy.invalid_rules", "정책 규칙(JSON) 이 유효하지 않습니다"),
    POLICY_ASSIGNMENT_INVALID("TLP-CDP-400-0003", 400,
            "error.cdp.policy.assignment_invalid", "정책 할당 정보가 유효하지 않습니다"),

    // ----------------- 403 권한 -----------------
    GLOBAL_CODE_READ_ONLY("TLP-CDP-403-0001", 403,
            "error.cdp.code.global_read_only", "글로벌 코드는 SYS_ADMIN 만 변경할 수 있습니다",
            "관리자만 수정할 수 있습니다."),

    // ----------------- 404 자원 -----------------
    CODE_GROUP_NOT_FOUND("TLP-CDP-404-0001", 404,
            "error.cdp.code_group.not_found", "코드 그룹을 찾을 수 없습니다"),
    CODE_NOT_FOUND("TLP-CDP-404-0002", 404,
            "error.cdp.code.not_found", "코드를 찾을 수 없습니다"),
    POLICY_NOT_FOUND("TLP-CDP-404-0003", 404,
            "error.cdp.policy.not_found", "정책을 찾을 수 없습니다"),

    // ----------------- 409 충돌 -----------------
    CODE_DUPLICATE("TLP-CDP-409-0001", 409,
            "error.cdp.code.duplicate", "이미 존재하는 코드입니다"),
    POLICY_DUPLICATE("TLP-CDP-409-0002", 409,
            "error.cdp.policy.duplicate", "이미 존재하는 정책 코드입니다"),
    POLICY_HAS_ASSIGNMENTS("TLP-CDP-409-0003", 409,
            "error.cdp.policy.has_assignments", "할당이 있는 정책은 삭제할 수 없습니다"),

    // ----------------- 422 비즈니스 -----------------
    EFFECTIVE_POLICY_NOT_RESOLVED("TLP-CDP-422-0001", 422,
            "error.cdp.policy.not_resolved", "효력 정책을 결정할 수 없습니다"),
    CODE_HIERARCHY_CYCLE("TLP-CDP-422-0002", 422,
            "error.cdp.code.hierarchy_cycle", "코드 계층 순환 참조가 감지되었습니다");

    private final String code;
    private final int httpStatus;
    private final String messageKey;
    private final String defaultMessage;
    private final String defaultUserMessage;

    CodePolicyErrorCode(String code, int httpStatus, String messageKey, String defaultMessage) {
        this(code, httpStatus, messageKey, defaultMessage, null);
    }

    CodePolicyErrorCode(String code, int httpStatus, String messageKey,
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
