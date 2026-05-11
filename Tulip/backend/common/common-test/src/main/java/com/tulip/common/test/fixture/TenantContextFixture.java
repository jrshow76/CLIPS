package com.tulip.common.test.fixture;

import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;

/**
 * 단위/통합 테스트에서 TenantContext 를 쉽게 주입하기 위한 헬퍼.
 *
 * <p>{@code try (var __ = TenantContextFixture.with("1", "1")) { ... }} 형태로 사용한다.
 * AutoCloseable 로 ThreadLocal 누수를 방지한다.</p>
 */
public final class TenantContextFixture implements AutoCloseable {

    private TenantContextFixture() {
    }

    /** 테스트용 컨텍스트를 설정한다. */
    public static TenantContextFixture with(String tenantId, String libraryId) {
        TenantContextHolder.set(new TenantContext(tenantId, libraryId, "test-user", "STAFF", false));
        return new TenantContextFixture();
    }

    /** 플랫폼 관리자 컨텍스트를 설정한다. */
    public static TenantContextFixture platformAdmin() {
        TenantContextHolder.set(new TenantContext("0", null, "platform-admin", "PLATFORM_ADMIN", true));
        return new TenantContextFixture();
    }

    @Override
    public void close() {
        TenantContextHolder.clear();
    }
}
