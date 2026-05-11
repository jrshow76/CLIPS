package com.tulip.gateway.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.security.jwt.JtiBlacklistChecker;
import com.tulip.common.security.jwt.JwtTokenProvider;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.gateway.config.GatewayProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * {@link JwtAuthenticationFilter} 단위 테스트.
 *
 * <p>JwtTokenProvider 와 블랙리스트를 mock 하여 헤더 강제 부착 및 401/403 매핑을 검증한다.</p>
 */
class JwtAuthenticationFilterTest {

    private JwtTokenProvider provider;
    private JtiBlacklistChecker blacklist;
    private GatewayProperties props;
    private ObjectMapper objectMapper;
    private GatewayFilterChain chain;
    private JwtAuthenticationFilter filter;

    @BeforeEach
    void setUp() {
        provider = mock(JwtTokenProvider.class);
        blacklist = mock(JtiBlacklistChecker.class);
        props = new GatewayProperties(new GatewayProperties.Security(
                "http://issuer", "http://jwks", Set.of("admin-web"),
                Set.of("/api/v1/auth/login/**", "/actuator/health")));
        objectMapper = new ObjectMapper();
        chain = mock(GatewayFilterChain.class);
        when(chain.filter(any())).thenReturn(Mono.empty());

        filter = new JwtAuthenticationFilter(provider, blacklist, props, objectMapper);
    }

    @Test
    void publicPath_는_인증_없이_통과한다() {
        ServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/auth/login/initiate"));
        StepVerifier.create(filter.filter(exchange, chain)).verifyComplete();
        assertThat(exchange.getResponse().getStatusCode()).isNull();
    }

    @Test
    void Authorization_헤더_누락_시_401_을_반환한다() {
        ServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/members/me"));
        StepVerifier.create(filter.filter(exchange, chain)).verifyComplete();
        assertThat(exchange.getResponse().getStatusCode().value()).isEqualTo(401);
    }

    @Test
    void 유효한_토큰의_경우_컨텍스트_헤더가_부착되고_체인이_통과된다() {
        TulipUserPrincipal principal = new TulipUserPrincipal(
                "user-1", "demo", List.of("main", "east"), "main",
                Set.of("LIBRARIAN"), Set.of("cir:read"),
                "STAFF", null, "jti-1");
        when(provider.validateAndExtract("good")).thenReturn(principal);
        when(blacklist.isBlacklisted(anyString())).thenReturn(false);

        ServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/members/me")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer good")
                        .header("X-Tenant-Id", "MALICIOUS")); // 클라이언트 헤더는 폐기되어야 한다

        when(chain.filter(any())).thenAnswer(inv -> {
            ServerWebExchange e = inv.getArgument(0);
            // 다운스트림 헤더 검증
            assertThat(e.getRequest().getHeaders().getFirst("X-User-Id")).isEqualTo("user-1");
            assertThat(e.getRequest().getHeaders().getFirst("X-Tenant-Id")).isEqualTo("demo");
            assertThat(e.getRequest().getHeaders().getFirst("X-Branch-Ids")).isEqualTo("main,east");
            assertThat(e.getRequest().getHeaders().getFirst("X-Roles")).isEqualTo("LIBRARIAN");
            return Mono.empty();
        });

        StepVerifier.create(filter.filter(exchange, chain)).verifyComplete();
    }

    @Test
    void 블랙리스트_jti_는_401_차단() {
        TulipUserPrincipal principal = new TulipUserPrincipal(
                "user-1", "demo", List.of("main"), "main",
                Set.of("LIBRARIAN"), Set.of(), "STAFF", null, "jti-blocked");
        when(provider.validateAndExtract("blocked")).thenReturn(principal);
        when(blacklist.isBlacklisted("jti-blocked")).thenReturn(true);

        ServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/members/me")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer blocked"));

        StepVerifier.create(filter.filter(exchange, chain)).verifyComplete();
        assertThat(exchange.getResponse().getStatusCode().value()).isEqualTo(401);
    }

    @Test
    void 검증_실패_시_401_을_반환한다() {
        when(provider.validateAndExtract("bad")).thenThrow(new RuntimeException("invalid signature"));

        ServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/members/me")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer bad"));

        StepVerifier.create(filter.filter(exchange, chain)).verifyComplete();
        assertThat(exchange.getResponse().getStatusCode().value()).isEqualTo(401);
    }

    @Test
    void tenant_claim_누락_시_403_을_반환한다() {
        TulipUserPrincipal principal = new TulipUserPrincipal(
                "user-1", null, List.of(), null,
                Set.of("LIBRARIAN"), Set.of(), "STAFF", null, "jti-1");
        when(provider.validateAndExtract("notenant")).thenReturn(principal);
        when(blacklist.isBlacklisted(anyString())).thenReturn(false);

        ServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/members/me")
                        .header(HttpHeaders.AUTHORIZATION, "Bearer notenant"));

        StepVerifier.create(filter.filter(exchange, chain)).verifyComplete();
        assertThat(exchange.getResponse().getStatusCode().value()).isEqualTo(403);
    }
}
