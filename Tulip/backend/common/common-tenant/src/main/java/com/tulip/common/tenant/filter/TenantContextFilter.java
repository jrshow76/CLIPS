package com.tulip.common.tenant.filter;

import com.tulip.common.core.trace.TraceContext;
import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * X-Tenant-Id / X-Library-Id 헤더를 ThreadLocal 컨텍스트로 옮기는 필터.
 *
 * <p>실제 운영에서는 Gateway 의 JWT 검증 결과로 헤더가 강제 부착된다.
 * Phase 1-A 본 모듈은 헤더에 의존하며, Phase 1-B 에서 JwtAuthenticationFilter 와 결합한다.</p>
 *
 * <p>주의: {@code finally} 에서 ThreadLocal 을 반드시 정리한다 (R-06 누수 방지).</p>
 */
public class TenantContextFilter extends OncePerRequestFilter implements Ordered {

    public static final String HEADER_TENANT_ID = "X-Tenant-Id";
    public static final String HEADER_LIBRARY_ID = "X-Library-Id";
    public static final String HEADER_USER_ID = "X-User-Id";
    public static final String HEADER_MEMBER_TYPE = "X-Member-Type";

    private final int order;

    public TenantContextFilter() {
        this(Ordered.HIGHEST_PRECEDENCE + 20);
    }

    public TenantContextFilter(int order) {
        this.order = order;
    }

    @Override
    public int getOrder() {
        return order;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String tenantId = request.getHeader(HEADER_TENANT_ID);
        String libraryId = request.getHeader(HEADER_LIBRARY_ID);
        String userId = request.getHeader(HEADER_USER_ID);
        String memberType = request.getHeader(HEADER_MEMBER_TYPE);

        TenantContext context = new TenantContext(
                tenantId,
                libraryId,
                userId,
                memberType,
                "PLATFORM_ADMIN".equalsIgnoreCase(memberType)
        );

        try {
            TenantContextHolder.set(context);
            if (tenantId != null) {
                MDC.put(TraceContext.MDC_TENANT_ID, tenantId);
            }
            if (userId != null) {
                MDC.put(TraceContext.MDC_USER_ID, userId);
            }
            chain.doFilter(request, response);
        } finally {
            TenantContextHolder.clear();
            MDC.remove(TraceContext.MDC_TENANT_ID);
            MDC.remove(TraceContext.MDC_USER_ID);
        }
    }
}
