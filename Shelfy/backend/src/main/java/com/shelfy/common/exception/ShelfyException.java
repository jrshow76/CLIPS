package com.shelfy.common.exception;

import lombok.Getter;

@Getter
public class ShelfyException extends RuntimeException {

    private final ErrorCode errorCode;

    public ShelfyException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.errorCode = errorCode;
    }

    public ShelfyException(ErrorCode errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }
}
