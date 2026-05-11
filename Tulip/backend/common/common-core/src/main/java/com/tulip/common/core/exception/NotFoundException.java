package com.tulip.common.core.exception;

import com.tulip.common.core.error.CommonErrorCode;
import com.tulip.common.core.error.ErrorCode;

/**
 * 자원을 찾을 수 없을 때 발생하는 예외 (HTTP 404).
 */
public class NotFoundException extends TulipException {

    public NotFoundException() {
        super(CommonErrorCode.RESOURCE_NOT_FOUND);
    }

    public NotFoundException(ErrorCode errorCode) {
        super(errorCode);
    }

    public NotFoundException(ErrorCode errorCode, String message) {
        super(errorCode, message);
    }
}
