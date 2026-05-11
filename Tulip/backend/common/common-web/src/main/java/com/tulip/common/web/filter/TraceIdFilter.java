package com.tulip.common.web.filter;

import com.tulip.common.core.trace.TraceContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 요청 단위 traceId 를 발급/전파하는 필터.
 *
 * <p>요청에 {@code traceparent} 또는 {@code X-Trace-Id} 가 있으면 재사용하고,
 * 없으면 W3C 형식으로 새로 발급한다. 응답 헤더와 MDC 에 동일 값을 채워 분산 추적을 지원한다.</p>
 *
 * <p>우선순위는 {@link Ordered#HIGHEST_PRECEDENCE} 직후로, TenantContextFilter 보다 먼저 동작한다.</p>
 */
public class TraceIdFilter extends OncePerRequestFilter implements Ordered {

    private final int order;

    public TraceIdFilter() {
        this(Ordered.HIGHEST_PRECEDENCE + 10);
    }

    public TraceIdFilter(int order) {
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
        String traceParent = request.getHeader(TraceContext.HEADER_TRACEPARENT);
        if (traceParent == null || traceParent.isBlank()) {
            traceParent = request.getHeader(TraceContext.HEADER_TRACE_ID);
        }
        if (traceParent == null || traceParent.isBlank()) {
            traceParent = TraceContext.newTraceParent();
        }

        String traceId = TraceContext.extractTraceId(traceParent);
        TraceContext.putTraceId(traceId);
        response.setHeader(TraceContext.HEADER_TRACEPARENT, traceParent);
        response.setHeader(TraceContext.HEADER_TRACE_ID, traceId);

        try {
            chain.doFilter(request, response);
        } finally {
            TraceContext.clear();
        }
    }
}
