package com.tulip.tenant.security;

/**
 * 현재 요청 스레드에서 RLS 적용에 사용할 (tenantId, role, bypass) 정보.
 *
 * <p>{@code TenantAuthFilter} 가 JWT/헤더로부터 채우고, {@code RlsTransactionAdvisor} 가
 * 트랜잭션 시작 시점에 SET LOCAL 로 적용한다.</p>
 */
public final class TenantSessionContext {

    private static final ThreadLocal<Holder> HOLDER = new ThreadLocal<>();

    public record Holder(Long tenantId, String role, boolean bypass) {
    }

    private TenantSessionContext() {
    }

    public static void set(Long tenantId, String role, boolean bypass) {
        HOLDER.set(new Holder(tenantId, role, bypass));
    }

    public static Holder get() {
        return HOLDER.get();
    }

    public static void clear() {
        HOLDER.remove();
    }
}
