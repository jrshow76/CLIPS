package com.tulip.common.core.exception;

import com.tulip.common.core.error.CommonErrorCode;
import com.tulip.common.core.error.ErrorCode;
import com.tulip.common.core.response.ErrorDetail;

import java.util.Collections;
import java.util.List;

/**
 * 입력 검증 실패(주로 HTTP 400) 예외.
 *
 * <p>Bean Validation 또는 수동 검증 단계에서 필드 오류를 표현한다.</p>
 */
public class ValidationException extends TulipException {

    private final List<ErrorDetail.FieldError> fieldErrors;

    public ValidationException(List<ErrorDetail.FieldError> fieldErrors) {
        super(CommonErrorCode.VALIDATION_REQUIRED);
        this.fieldErrors = fieldErrors == null ? Collections.emptyList() : List.copyOf(fieldErrors);
    }

    public ValidationException(ErrorCode errorCode, String message, List<ErrorDetail.FieldError> fieldErrors) {
        super(errorCode, message);
        this.fieldErrors = fieldErrors == null ? Collections.emptyList() : List.copyOf(fieldErrors);
    }

    public List<ErrorDetail.FieldError> fieldErrors() {
        return fieldErrors;
    }
}
