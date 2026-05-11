package com.tulip.tenant.infra.mapper.params;

/**
 * 테넌트 검색 매퍼 파라미터.
 */
public record TenantSearchParam(
        String code,
        String name,
        String status,
        int offset,
        int limit
) {
}
