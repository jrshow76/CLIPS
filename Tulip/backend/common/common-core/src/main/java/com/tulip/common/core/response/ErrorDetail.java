package com.tulip.common.core.response;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;
import java.util.Map;

/**
 * 오류 응답 상세 블록.
 *
 * <p>응답 envelope 에 포함되며, 운영 환경에서는 {@code debug} 가 자동 마스킹된다.</p>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ErrorDetail(
        String messageKey,
        String userMessage,
        List<FieldError> fieldErrors,
        Map<String, Object> debug
) {

    /** 입력 검증 실패 항목 단위. */
    public record FieldError(String field, String message, Object rejectedValue) {
    }

    /** 단순 message 만 포함하는 detail 생성. */
    public static ErrorDetail of(String messageKey, String userMessage) {
        return new ErrorDetail(messageKey, userMessage, null, null);
    }
}
