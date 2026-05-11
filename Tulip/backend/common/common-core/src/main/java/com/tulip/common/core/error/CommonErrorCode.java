package com.tulip.common.core.error;

/**
 * 공통(CMN)·시스템(SYS) 도메인 표준 에러 코드 집합.
 *
 * <p>도메인 서비스는 자신의 {@code XxxErrorCode} enum 을 별도로 정의하되 본 인터페이스를 구현한다.
 * 본 enum 은 {@code 04_error_codes.md} §5.2, §5.3 발췌이며, 도메인 서비스가 공통적으로 참조한다.</p>
 */
public enum CommonErrorCode implements ErrorCode {

    // ----------------- 400 입력 검증 -----------------
    VALIDATION_REQUIRED("TLP-CMN-400-0001", 400,
            "error.cmn.validation.required", "필수값이 누락되었습니다"),
    VALIDATION_FORMAT("TLP-CMN-400-0002", 400,
            "error.cmn.validation.format", "입력 형식이 올바르지 않습니다"),
    VALIDATION_RANGE("TLP-CMN-400-0003", 400,
            "error.cmn.validation.range", "입력값이 허용 범위를 벗어났습니다"),
    VALIDATION_LENGTH("TLP-CMN-400-0004", 400,
            "error.cmn.validation.length", "입력 길이가 허용 범위를 벗어났습니다"),
    VALIDATION_INVALID_ENUM("TLP-CMN-400-0005", 400,
            "error.cmn.validation.invalid_enum", "유효하지 않은 코드값입니다"),

    // ----------------- 404 자원 -----------------
    RESOURCE_NOT_FOUND("TLP-CMN-404-0001", 404,
            "error.cmn.resource.not_found", "요청하신 자원을 찾을 수 없습니다"),

    // ----------------- 409 충돌 -----------------
    DUPLICATE_ENTITY("TLP-CMN-409-0001", 409,
            "error.cmn.duplicate.entity", "이미 존재하는 데이터입니다"),
    STATE_CONFLICT("TLP-CMN-409-0003", 409,
            "error.cmn.state.conflict", "현재 상태에서 작업을 수행할 수 없습니다"),
    ETAG_MISMATCH("TLP-CMN-409-0004", 409,
            "error.cmn.etag.mismatch", "다른 사용자가 먼저 수정했습니다"),

    // ----------------- 422 비즈니스 -----------------
    POLICY_VIOLATION("TLP-CMN-422-0001", 422,
            "error.cmn.policy.violation", "정책을 위반했습니다"),

    // ----------------- 429 Rate Limit -----------------
    RATE_LIMIT_EXCEEDED("TLP-CMN-429-0001", 429,
            "error.cmn.rate_limit.exceeded", "요청이 너무 많습니다"),

    // ----------------- 500/503 시스템 -----------------
    SYSTEM_UNKNOWN("TLP-CMN-500-0001", 500,
            "error.cmn.system.unknown", "시스템 오류가 발생했습니다"),
    SYSTEM_MAINTENANCE("TLP-CMN-503-0001", 503,
            "error.cmn.system.maintenance", "시스템 점검 중입니다"),

    // ----------------- SYS (인프라) -----------------
    SYS_DB_CONNECTION("TLP-SYS-500-0001", 500,
            "error.sys.db.connection", "데이터베이스 연결 실패"),
    SYS_DB_DEADLOCK("TLP-SYS-500-0002", 500,
            "error.sys.db.deadlock", "데이터 처리 충돌이 발생했습니다"),
    SYS_DEPENDENCY_UNAVAILABLE("TLP-SYS-503-0001", 503,
            "error.sys.dependency.unavailable", "의존 서비스를 사용할 수 없습니다"),
    SYS_TIMEOUT("TLP-SYS-504-0001", 504,
            "error.sys.timeout", "처리 시간 초과");

    private final String code;
    private final int httpStatus;
    private final String messageKey;
    private final String defaultMessage;

    CommonErrorCode(String code, int httpStatus, String messageKey, String defaultMessage) {
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
