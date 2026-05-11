package com.tulip.common.web.advice;

import com.tulip.common.core.error.CommonErrorCode;
import com.tulip.common.core.error.ErrorCode;
import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.exception.TulipException;
import com.tulip.common.core.exception.ValidationException;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.core.response.ErrorDetail;
import com.tulip.common.core.trace.TraceContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.List;

/**
 * Tulip+ 전 서비스 공통 예외 핸들러.
 *
 * <p>{@link TulipException} 계층을 {@link ApiResponse} envelope 으로 일관 변환한다.
 * 운영 환경에서는 {@code debug} 블록을 자동 마스킹한다 ({@code 03_api_standards.md} §4.1).</p>
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /** 입력 검증 실패 (Bean Validation). */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException ex) {
        List<ErrorDetail.FieldError> fieldErrors = ex.getBindingResult().getFieldErrors().stream()
                .map(fe -> new ErrorDetail.FieldError(fe.getField(), fe.getDefaultMessage(), fe.getRejectedValue()))
                .toList();
        ErrorCode code = CommonErrorCode.VALIDATION_REQUIRED;
        ErrorDetail detail = new ErrorDetail(code.messageKey(), null, fieldErrors, null);
        return build(code, code.defaultMessage(), detail);
    }

    /** 커스텀 검증 예외. */
    @ExceptionHandler(ValidationException.class)
    public ResponseEntity<ApiResponse<Void>> handleCustomValidation(ValidationException ex) {
        ErrorCode code = ex.errorCode();
        ErrorDetail detail = new ErrorDetail(code.messageKey(), null, ex.fieldErrors(), null);
        return build(code, ex.getMessage(), detail);
    }

    /** 자원 미존재. */
    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleNotFound(NotFoundException ex) {
        ErrorCode code = ex.errorCode();
        return build(code, ex.getMessage(), ErrorDetail.of(code.messageKey(), code.defaultUserMessage()));
    }

    /** 모든 Tulip 도메인 예외. */
    @ExceptionHandler(TulipException.class)
    public ResponseEntity<ApiResponse<Void>> handleTulip(TulipException ex) {
        ErrorCode code = ex.errorCode();
        if (code.httpStatus() >= 500) {
            log.error("도메인 예외 발생 code={} message={}", code.code(), ex.getMessage(), ex);
        } else {
            log.warn("비즈니스 예외 code={} message={}", code.code(), ex.getMessage());
        }
        return build(code, ex.getMessage(), ErrorDetail.of(code.messageKey(), code.defaultUserMessage()));
    }

    /** 잘못된 JSON 등 메시지 변환 오류. */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ApiResponse<Void>> handleNotReadable(HttpMessageNotReadableException ex) {
        ErrorCode code = CommonErrorCode.VALIDATION_FORMAT;
        return build(code, code.defaultMessage(), ErrorDetail.of(code.messageKey(), null));
    }

    /** 마지막 안전망 — 미처리 예외. */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleUnknown(Exception ex) {
        log.error("미처리 예외", ex);
        ErrorCode code = CommonErrorCode.SYSTEM_UNKNOWN;
        return build(code, code.defaultMessage(), ErrorDetail.of(code.messageKey(), null));
    }

    private ResponseEntity<ApiResponse<Void>> build(ErrorCode code, String message, ErrorDetail detail) {
        ApiResponse<Void> body = ApiResponse.<Void>failure(code.code(), message, detail)
                .withTraceId(TraceContext.currentTraceId());
        return ResponseEntity.status(HttpStatus.valueOf(code.httpStatus())).body(body);
    }
}
