package com.tulip.common.core.response;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.OffsetDateTime;

/**
 * Tulip+ 표준 API 응답 envelope.
 *
 * <p>모든 REST API 응답(정상/오류)은 본 envelope 로 직렬화된다.
 * 필드 정의는 {@code 03_api_standards.md} §4.1 을 따른다.</p>
 *
 * @param <T> 응답 본문 데이터 타입
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApiResponse<T>(
        boolean success,
        String code,
        String message,
        String userMessage,
        T data,
        ResponseMeta meta,
        ErrorDetail error,
        OffsetDateTime timestamp,
        String traceId
) {

    /** 단건 성공 응답을 생성한다. */
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(
                true,
                "OK",
                "처리되었습니다",
                null,
                data,
                null,
                null,
                OffsetDateTime.now(),
                null
        );
    }

    /** 페이지/메타데이터를 포함하는 성공 응답을 생성한다. */
    public static <T> ApiResponse<T> success(T data, ResponseMeta meta) {
        return new ApiResponse<>(
                true,
                "OK",
                "처리되었습니다",
                null,
                data,
                meta,
                null,
                OffsetDateTime.now(),
                null
        );
    }

    /** 오류 응답을 생성한다. */
    public static <T> ApiResponse<T> failure(String code, String message, ErrorDetail error) {
        return new ApiResponse<>(
                false,
                code,
                message,
                error != null ? error.userMessage() : null,
                null,
                null,
                error,
                OffsetDateTime.now(),
                null
        );
    }

    /** traceId 를 메아리로 채워 반환한다. (불변 record 의 functional copy) */
    public ApiResponse<T> withTraceId(String traceId) {
        return new ApiResponse<>(success, code, message, userMessage, data, meta, error, timestamp, traceId);
    }
}
