package com.tulip.tenant.infra.mapper.params;

/**
 * 라이브러리 검색 매퍼 파라미터. tenant_id 는 RLS 가 강제하므로 명시 제외.
 */
public record LibrarySearchParam(
        String name,
        String status,
        int offset,
        int limit
) {
}
