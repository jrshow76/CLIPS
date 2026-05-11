package com.tulip.gateway.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.core.response.ErrorDetail;
import com.tulip.common.security.error.AuthErrorCode;
import com.tulip.gateway.config.GatewayProperties;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.io.IOException;

/**
 * Tenant 헤더 누락 차단 보조 필터.
 *
 * <p>{@link JwtAuthenticationFilter} 이후에 실행되며, 보호된 경로에 대해
 * {@code X-Tenant-Id} 헤더가 비어있으면 403(TLP-AUT-403-0002) 으로 차단한다.</p>
 *
 * <p>이중 검증의 목적: JWT 검증 단계의 누락·우회 가능성을 한 번 더 차단한다(Defense in Depth).</p>
 */
@Component
public class TenantHeaderEnricherFilter implements GlobalFilter, Ordered {

    private final GatewayProperties props;
    private final ObjectMapper objectMapper;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    public TenantHeaderEnricherFilter(GatewayProperties props, ObjectMapper objectMapper) {
        this.props = props;
        this.objectMapper = objectMapper;
    }

    @Override
    public int getOrder() {
        return -90; // JwtAuthenticationFilter(-100) 직후
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();
        if (isPublic(path)) {
            return chain.filter(exchange);
        }
        String tenantId = exchange.getRequest().getHeaders().getFirst("X-Tenant-Id");
        String roles = exchange.getRequest().getHeaders().getFirst("X-Roles");
        boolean platformAdmin = roles != null && (roles.contains("PLATFORM_ADMIN") || roles.contains("SYS_ADMIN"));
        if ((tenantId == null || tenantId.isBlank()) && !platformAdmin) {
            return writeError(exchange);
        }
        return chain.filter(exchange);
    }

    private boolean isPublic(String path) {
        if (props.security() == null || props.security().publicPaths() == null) {
            return false;
        }
        return props.security().publicPaths().stream()
                .anyMatch(p -> pathMatcher.match(p, path));
    }

    private Mono<Void> writeError(ServerWebExchange exchange) {
        AuthErrorCode code = AuthErrorCode.TENANT_MISMATCH;
        ServerHttpResponse response = exchange.getResponse();
        response.setRawStatusCode(code.httpStatus());
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        ApiResponse<Void> body = ApiResponse.<Void>failure(
                code.code(),
                code.defaultMessage(),
                ErrorDetail.of(code.messageKey(), code.defaultUserMessage()));
        try {
            byte[] bytes = objectMapper.writeValueAsBytes(body);
            DataBuffer buffer = response.bufferFactory().wrap(bytes);
            return response.writeWith(Mono.just(buffer));
        } catch (IOException e) {
            return response.setComplete();
        }
    }
}
