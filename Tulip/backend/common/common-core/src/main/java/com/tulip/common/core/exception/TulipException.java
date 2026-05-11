package com.tulip.common.core.exception;

import com.tulip.common.core.error.ErrorCode;

import java.util.Collections;
import java.util.Map;

/**
 * Tulip+ 도메인 예외의 추상 부모.
 *
 * <p>모든 비즈니스/인프라 예외는 본 클래스를 상속하여 {@link ErrorCode} 를 의무 부착한다.
 * GlobalExceptionHandler 가 본 타입을 일관된 envelope 로 변환한다.</p>
 */
public abstract class TulipException extends RuntimeException {

    private final ErrorCode errorCode;
    private final transient Map<String, Object> details;

    protected TulipException(ErrorCode errorCode) {
        super(errorCode.defaultMessage());
        this.errorCode = errorCode;
        this.details = Collections.emptyMap();
    }

    protected TulipException(ErrorCode errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
        this.details = Collections.emptyMap();
    }

    protected TulipException(ErrorCode errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.details = Collections.emptyMap();
    }

    protected TulipException(ErrorCode errorCode, String message, Map<String, Object> details, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.details = details == null ? Collections.emptyMap() : Collections.unmodifiableMap(details);
    }

    /** 에러 코드. */
    public ErrorCode errorCode() {
        return errorCode;
    }

    /** 디버그용 상세 컨텍스트 (운영 환경에서는 마스킹 권장). */
    public Map<String, Object> details() {
        return details;
    }
}
