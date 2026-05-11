package com.tulip.common.web.filter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 요청 단위 액세스 로그 필터.
 *
 * <p>method / path / status / duration 을 INFO 레벨로 한 줄 출력한다.
 * 페이로드 본문은 PII 노출 위험으로 출력하지 않는다 ({@code 06_coding_standards} §9 PII 정책).</p>
 */
public class RequestLoggingFilter extends OncePerRequestFilter implements Ordered {

    private static final Logger ACCESS_LOG = LoggerFactory.getLogger("ACCESS");

    private final int order;

    public RequestLoggingFilter() {
        this(Ordered.HIGHEST_PRECEDENCE + 30);
    }

    public RequestLoggingFilter(int order) {
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
        long start = System.nanoTime();
        try {
            chain.doFilter(request, response);
        } finally {
            long durationMs = (System.nanoTime() - start) / 1_000_000L;
            ACCESS_LOG.info("method={} path={} status={} durationMs={}",
                    request.getMethod(),
                    request.getRequestURI(),
                    response.getStatus(),
                    durationMs);
        }
    }
}
