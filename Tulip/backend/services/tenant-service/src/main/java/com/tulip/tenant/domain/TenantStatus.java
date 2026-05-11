package com.tulip.tenant.domain;

/**
 * 테넌트/라이브러리/분관 상태 enum.
 *
 * <p>DBA 마이그레이션의 CHECK 제약 ({@code 'ACTIVE'|'SUSPENDED'|'CLOSED'}) 과 동일하다.</p>
 */
public enum TenantStatus {
    ACTIVE,
    SUSPENDED,
    CLOSED;

    /** 문자열 -> enum, 대소문자 무시. 미지의 값은 null. */
    public static TenantStatus parseOrNull(String value) {
        if (value == null) {
            return null;
        }
        try {
            return TenantStatus.valueOf(value.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
