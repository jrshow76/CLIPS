package com.tulip.common.core.page;

/**
 * 페이지네이션 요청 객체.
 *
 * <p>offset/limit 기반 또는 cursor 기반을 모두 표현한다.
 * 도메인 서비스는 본 객체를 받아 Mapper 파라미터로 전달한다.</p>
 *
 * @param type    "offset" 또는 "cursor"
 * @param page    1-base 페이지 번호 (offset 형)
 * @param size    페이지 크기 (offset 형, 최대 100)
 * @param cursor  base64 인코딩된 커서 (cursor 형)
 * @param limit   커서 한계 (cursor 형, 최대 200)
 */
public record Pagination(
        String type,
        Integer page,
        Integer size,
        String cursor,
        Integer limit
) {

    private static final int MAX_OFFSET_SIZE = 100;
    private static final int MAX_CURSOR_LIMIT = 200;

    /** 기본 offset 페이지(1, 20)를 생성한다. */
    public static Pagination defaults() {
        return new Pagination("offset", 1, 20, null, null);
    }

    /** offset 기반 페이지를 생성한다 (size 가 최대치를 넘으면 캡). */
    public static Pagination offset(int page, int size) {
        int capped = Math.min(Math.max(size, 1), MAX_OFFSET_SIZE);
        int normalizedPage = Math.max(page, 1);
        return new Pagination("offset", normalizedPage, capped, null, null);
    }

    /** cursor 기반 페이지를 생성한다 (limit 가 최대치를 넘으면 캡). */
    public static Pagination cursor(String cursor, int limit) {
        int capped = Math.min(Math.max(limit, 1), MAX_CURSOR_LIMIT);
        return new Pagination("cursor", null, null, cursor, capped);
    }

    /** offset 타입의 SQL OFFSET 값을 계산한다. */
    public int sqlOffset() {
        if (!"offset".equals(type) || page == null || size == null) {
            return 0;
        }
        return (page - 1) * size;
    }

    /** offset 또는 cursor 의 실제 페이지 크기를 반환한다. */
    public int effectiveSize() {
        if ("cursor".equals(type) && limit != null) {
            return limit;
        }
        return size == null ? 20 : size;
    }
}
