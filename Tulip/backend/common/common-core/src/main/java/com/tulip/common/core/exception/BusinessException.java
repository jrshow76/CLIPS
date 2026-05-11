package com.tulip.common.core.exception;

import com.tulip.common.core.error.ErrorCode;

import java.util.Map;

/**
 * 비즈니스 규칙 위반(주로 HTTP 422) 예외.
 *
 * <p>예: 대출 권수 한도 초과, 예산 부족, 출입 정책 위반 등.
 * 상태 충돌(409)은 별도의 ConflictException 또는 본 클래스로 동일하게 표현 가능하다.</p>
 */
public class BusinessException extends TulipException {

    public BusinessException(ErrorCode errorCode) {
        super(errorCode);
    }

    public BusinessException(ErrorCode errorCode, String message) {
        super(errorCode, message);
    }

    public BusinessException(ErrorCode errorCode, String message, Map<String, Object> details) {
        super(errorCode, message, details, null);
    }

    public BusinessException(ErrorCode errorCode, String message, Throwable cause) {
        super(errorCode, message, cause);
    }
}
