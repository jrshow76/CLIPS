package com.tulip.gateway.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.core.response.ErrorDetail;
import com.tulip.common.security.error.AuthErrorCode;
import com.tulip.common.security.jwt.JtiBlacklistChecker;
import com.tulip.common.security.jwt.JwtTokenProvider;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.gateway.config.GatewayProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.io.IOException;
import java.util.List;

/**
 * Gateway 의 핵심 GlobalFilter — JWT 검증 + JTI 블랙리스트 + 컨텍스트 헤더 전파.
 *
 * <p>{@code 05_security_and_auth.md} §4.2 의 강제 흐름을 구현한다.</p>
 *
 * <p>요청 처리 단계:</p>
 * <ol>
 *   <li>publicPaths 화이트리스트는 그대로 통과 (인증 없음).</li>
 *   <li>Authorization Bearer 토큰 추출 → 누락 시 401(TLP-AUT-401-0001).</li>
 *   <li>JwtTokenProvider 로 서명·iss·aud·exp 검증.</li>
 *   <li>JTI 블랙리스트 검사 (Redis).</li>
 *   <li>tenant claim 누락 시 403(TLP-AUT-403-0002).</li>
 *   <li>X-User-Id / X-Tenant-Id / X-Branch-Ids / X-Roles / X-Trace-Id 헤더로 다운스트림 전파.
 *       클라이언트가 보낸 동일 헤더는 보안상 폐기 후 재발급한다.</li>
 * </ol>
 */
@Component
public class JwtAuthenticationFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(JwtAuthenticationFilter.class);
    private static final String BEARER = "Bearer ";

    private final JwtTokenProvider jwtProvider;
    private final JtiBlacklistChecker blacklist;
    private final GatewayProperties props;
    private final ObjectMapper objectMapper;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    public JwtAuthenticationFilter(JwtTokenProvider jwtProvider,
                                   JtiBlacklistChecker blacklist,
                                   GatewayProperties props,
                                   ObjectMapper objectMapper) {
        this.jwtProvider = jwtProvider;
        this.blacklist = blacklist;
        this.props = props;
        this.objectMapper = objectMapper;
    }

    @Override
    public int getOrder() {
        // CORS·Trace 다음, 라우팅 직전
        return -100;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        if (isPublic(path)) {
            return chain.filter(exchange);
        }

        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.startsWith(BEARER)) {
            return writeError(exchange, AuthErrorCode.TOKEN_MISSING);
        }
        String token = authHeader.substring(BEARER.length()).trim();

        return Mono.fromCallable(() -> jwtProvider.validateAndExtract(token))
                .subscribeOn(Schedulers.boundedElastic())
                .onErrorResume(ex -> Mono.error(new InvalidTokenSignal(pickCode(ex))))
                .flatMap(principal -> {
                    if (principal.tokenId() != null && blacklist.isBlacklisted(principal.tokenId())) {
                        return writeError(exchange, AuthErrorCode.TOKEN_INVALID);
                    }
                    if (principal.tenantId() == null || principal.tenantId().isBlank()) {
                        // PLATFORM_ADMIN 은 tenant 없이도 허용 (헤더 강제 전환 가능)
                        if (!isPlatformAdmin(principal)) {
                            return writeError(exchange, AuthErrorCode.TENANT_MISMATCH);
                        }
                    }
                    ServerHttpRequest mutated = stripAndEnrich(request, principal);
                    return chain.filter(exchange.mutate().request(mutated).build());
                })
                .onErrorResume(InvalidTokenSignal.class, sig -> writeError(exchange, sig.code));
    }

    /* ============================== helpers ============================== */

    private boolean isPublic(String path) {
        if (props.security() == null || props.security().publicPaths() == null) {
            return false;
        }
        return props.security().publicPaths().stream()
                .anyMatch(p -> pathMatcher.match(p, path));
    }

    private static boolean isPlatformAdmin(TulipUserPrincipal p) {
        return p.hasRole("PLATFORM_ADMIN") || p.hasRole("SYS_ADMIN");
    }

    /** 클라이언트가 보낸 보안 헤더는 폐기하고 JWT 클레임 기반으로 재발급한다. */
    private ServerHttpRequest stripAndEnrich(ServerHttpRequest request, TulipUserPrincipal principal) {
        // PLATFORM_ADMIN 은 X-Tenant-Id 헤더로 임의 전환 허용
        String overrideTenant = null;
        if (isPlatformAdmin(principal)) {
            overrideTenant = request.getHeaders().getFirst("X-Tenant-Id");
        }
        String tenantId = overrideTenant != null && !overrideTenant.isBlank()
                ? overrideTenant : principal.tenantId();

        return request.mutate()
                .headers(h -> {
                    h.remove("X-User-Id");
                    h.remove("X-Tenant-Id");
                    h.remove("X-Branch-Ids");
                    h.remove("X-Roles");
                    h.remove("X-Member-Type");
                    if (principal.userId() != null) h.set("X-User-Id", principal.userId());
                    if (tenantId != null) h.set("X-Tenant-Id", tenantId);
                    if (principal.libraryIds() != null && !principal.libraryIds().isEmpty()) {
                        h.set("X-Branch-Ids", String.join(",", principal.libraryIds()));
                    }
                    if (principal.roles() != null && !principal.roles().isEmpty()) {
                        h.set("X-Roles", String.join(",", principal.roles()));
                    }
                    if (principal.memberType() != null) h.set("X-Member-Type", principal.memberType());
                    if (h.getFirst("X-Trace-Id") == null) {
                        String trace = principal.tokenId() != null ? principal.tokenId() : java.util.UUID.randomUUID().toString();
                        h.set("X-Trace-Id", trace);
                    }
                })
                .build();
    }

    private AuthErrorCode pickCode(Throwable ex) {
        String msg = ex.getMessage() == null ? "" : ex.getMessage().toLowerCase();
        if (msg.contains("expired")) return AuthErrorCode.TOKEN_EXPIRED;
        return AuthErrorCode.TOKEN_INVALID;
    }

    private Mono<Void> writeError(ServerWebExchange exchange, AuthErrorCode code) {
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
            log.error("응답 직렬화 실패", e);
            return response.setComplete();
        }
    }

    /** 내부 신호 — 인증 실패 코드를 onErrorResume 으로 전달. */
    private static final class InvalidTokenSignal extends RuntimeException {
        final AuthErrorCode code;
        InvalidTokenSignal(AuthErrorCode code) {
            super(code.defaultMessage());
            this.code = code;
        }
    }

    public static List<String> defaultExposedHeaders() {
        return List.of("X-Trace-Id", "ETag", "Location", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset");
    }
}
