package com.tulip.tenant.application;

import com.tulip.common.core.response.ResponseMeta;

/**
 * offset/limit 기반 페이지네이션 메타 생성 헬퍼.
 *
 * <p>본 도메인은 모두 offset-pagination 으로 통일하며, cursor 는 향후 검색 API 가 적용한다.
 * {@link ResponseMeta#offset(long, int, int)} 의 thin wrapper.</p>
 */
public final class PageMetaBuilder {

    private PageMetaBuilder() {
    }

    public static ResponseMeta offsetMeta(int offset, int limit, long total) {
        int safeLimit = Math.max(1, limit);
        int number = offset / safeLimit;
        return ResponseMeta.offset(total, number, safeLimit);
    }
}
