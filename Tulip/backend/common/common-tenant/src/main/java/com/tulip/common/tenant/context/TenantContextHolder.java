package com.tulip.common.tenant.context;

/**
 * 요청 스레드 별 {@link TenantContext} 보관소.
 *
 * <p>{@code TenantContextFilter} 가 요청 진입 시 채우고, 응답 종료 시 {@link #clear()} 한다.
 * 서비스/매퍼는 본 홀더를 통해 현재 테넌트를 조회한다.</p>
 */
public final class TenantContextHolder {

    private static final ThreadLocal<TenantContext> HOLDER = new ThreadLocal<>();

    private TenantContextHolder() {
    }

    /** 현재 스레드의 컨텍스트 (없으면 null). */
    public static TenantContext get() {
        return HOLDER.get();
    }

    /** 컨텍스트가 비어있을 경우 예외, 아니면 반환. */
    public static TenantContext require() {
        TenantContext ctx = HOLDER.get();
        if (ctx == null || ctx.isEmpty()) {
            throw new IllegalStateException("TenantContext 가 비어있습니다. TenantContextFilter 적용 여부를 확인하세요.");
        }
        return ctx;
    }

    /** 컨텍스트를 설정한다. */
    public static void set(TenantContext context) {
        HOLDER.set(context);
    }

    /** 스레드 누수를 방지하기 위해 요청 종료 시점에 반드시 호출. */
    public static void clear() {
        HOLDER.remove();
    }
}
