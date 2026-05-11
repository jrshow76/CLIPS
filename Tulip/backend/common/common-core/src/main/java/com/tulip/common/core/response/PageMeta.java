package com.tulip.common.core.response;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * 페이지네이션 메타데이터.
 *
 * <p>{@code type} 가 {@code "offset"} 인 경우 number/size/totalElements/totalPages 를,
 * {@code "cursor"} 인 경우 limit/next 를 사용한다.</p>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record PageMeta(
        String type,
        Integer number,
        Integer size,
        Long totalElements,
        Integer totalPages,
        Integer limit,
        String next
) {
}
