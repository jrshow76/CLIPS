package com.tulip.common.core.response;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;
import java.util.Map;

/**
 * 응답 envelope 의 메타데이터 블록.
 *
 * <p>페이지 정보, 정렬, 필터, 테넌트 컨텍스트를 함께 표현한다.</p>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ResponseMeta(
        String tenantId,
        String libraryId,
        PageMeta page,
        List<String> sort,
        Map<String, Object> filter
) {

    /** offset 기반 페이지 메타. */
    public static ResponseMeta offset(long totalElements, int pageNumber, int pageSize) {
        int totalPages = pageSize == 0 ? 0 : (int) Math.ceil((double) totalElements / pageSize);
        return new ResponseMeta(
                null, null,
                new PageMeta("offset", pageNumber, pageSize, totalElements, totalPages, null, null),
                null, null
        );
    }

    /** cursor 기반 페이지 메타. */
    public static ResponseMeta cursor(int limit, String next) {
        return new ResponseMeta(
                null, null,
                new PageMeta("cursor", null, null, null, null, limit, next),
                null, null
        );
    }
}
