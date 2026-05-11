package com.tulip.iam.auth.service;

import com.tulip.common.security.jwt.JwtTokenProvider;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.iam.auth.dto.LoginDtos;
import com.tulip.iam.auth.repository.IamRefreshAuditRepository;
import com.tulip.iam.auth.repository.IamUserLinkRepository;
import com.tulip.iam.config.IamProperties;
import com.tulip.iam.keycloak.KeycloakClient;
import com.tulip.iam.security.PkceStateStore;
import com.tulip.iam.security.RedisJtiBlacklist;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * {@link AuthService} 단위 테스트.
 *
 * <p>Keycloak/Redis/JWT 의존성을 모두 Mockito 로 대체하여 로직만 검증한다.</p>
 */
class AuthServiceTest {

    private PkceStateStore pkceStore;
    private KeycloakClient keycloak;
    private JwtTokenProvider jwtProvider;
    private RedisJtiBlacklist blacklist;
    private IamUserLinkRepository userLinkRepo;
    private IamRefreshAuditRepository auditRepo;
    private IamProperties props;

    private AuthService authService;

    @BeforeEach
    void setUp() {
        pkceStore = mock(PkceStateStore.class);
        keycloak = mock(KeycloakClient.class);
        jwtProvider = mock(JwtTokenProvider.class);
        blacklist = mock(RedisJtiBlacklist.class);
        userLinkRepo = mock(IamUserLinkRepository.class);
        auditRepo = mock(IamRefreshAuditRepository.class);

        props = new IamProperties(
                new IamProperties.Keycloak(
                        "http://localhost/realms/tulip",
                        "http://localhost/auth",
                        "http://localhost/token",
                        "http://localhost/logout",
                        "http://localhost/certs",
                        "iam-service",
                        "secret",
                        "http://localhost:8101/api/v1/auth/login/callback",
                        List.of()),
                Set.of("admin-web"),
                new IamProperties.Cookie("tulip_rt", "/api/v1/auth", "Lax", false, Duration.ofHours(12)),
                Duration.ofMinutes(5)
        );

        authService = new AuthService(props, pkceStore, keycloak, jwtProvider, blacklist, userLinkRepo, auditRepo);
    }

    @Test
    void initiate_은_PKCE_state_와_authorize_URL_을_생성한다() {
        LoginDtos.InitiateResponse resp = authService.initiate(new LoginDtos.InitiateRequest(null, null));

        assertThat(resp.state()).isNotBlank();
        assertThat(resp.codeChallenge()).isNotBlank();
        assertThat(resp.codeChallengeMethod()).isEqualTo("S256");
        assertThat(resp.authorizeUrl()).contains("http://localhost/auth")
                .contains("client_id=iam-service")
                .contains("code_challenge_method=S256");
        verify(pkceStore, times(1)).put(anyString(), anyString(), anyString());
    }

    @Test
    void callback_은_token_교환_후_principal_을_반환하고_링크_업서트를_수행한다() {
        when(pkceStore.consume("state-1"))
                .thenReturn(new PkceStateStore.PkceEntry("http://cb", "verifier-1"));
        when(keycloak.exchangeCode("code-1", "http://cb", "verifier-1"))
                .thenReturn(Map.of(
                        "access_token", "at",
                        "refresh_token", "rt",
                        "expires_in", 300,
                        "scope", "openid"));
        TulipUserPrincipal principal = new TulipUserPrincipal(
                "user-1", "demo", List.of("main"), "main",
                Set.of("LIBRARIAN"), Set.of("cir:read"),
                "STAFF", null, "jti-at");
        when(jwtProvider.validateAndExtract("at")).thenReturn(principal);

        AuthService.TokenExchangeResult result = authService.callback(
                new LoginDtos.CallbackRequest("code-1", "state-1"),
                "127.0.0.1", "JUnit");

        assertThat(result.accessToken()).isEqualTo("at");
        assertThat(result.refreshToken()).isEqualTo("rt");
        assertThat(result.expiresIn()).isEqualTo(300);
        verify(userLinkRepo).upsert("user-1", "user-1", "demo", "main");
        verify(auditRepo).record("user-1", "issue", "127.0.0.1", "JUnit");
    }

    @Test
    void rotateRefresh_는_구_jti_를_블랙리스트에_등록하고_새_토큰을_반환한다() {
        when(jwtProvider.tokenId("rt-old")).thenReturn("jti-old");
        when(keycloak.refresh("rt-old"))
                .thenReturn(Map.of(
                        "access_token", "at-new",
                        "refresh_token", "rt-new",
                        "expires_in", 300));
        TulipUserPrincipal principal = new TulipUserPrincipal(
                "user-1", "demo", List.of(), null,
                Set.of("LIBRARIAN"), Set.of(),
                "STAFF", null, "jti-at-new");
        when(jwtProvider.validateAndExtract("at-new")).thenReturn(principal);

        AuthService.TokenExchangeResult result = authService.rotateRefresh("rt-old", "127.0.0.1", "JUnit");

        assertThat(result.accessToken()).isEqualTo("at-new");
        verify(blacklist).blacklist(eq("jti-old"), any(Instant.class), anyString());
        verify(auditRepo).record("user-1", "rotate", "127.0.0.1", "JUnit");
    }

    @Test
    void logout_은_access_jti_와_refresh_jti_를_모두_블랙리스트에_등록하고_endSession_호출한다() {
        when(jwtProvider.tokenId("at")).thenReturn("jti-at");
        when(jwtProvider.tokenId("rt")).thenReturn("jti-rt");
        TulipUserPrincipal principal = new TulipUserPrincipal(
                "user-1", "demo", List.of(), null, Set.of(), Set.of(), "STAFF", null, "jti-at");
        when(jwtProvider.validateAndExtract("at")).thenReturn(principal);

        authService.logout("at", "rt", "127.0.0.1", "JUnit");

        verify(blacklist).blacklist(eq("jti-at"), any(Instant.class), anyString());
        verify(blacklist).blacklist(eq("jti-rt"), any(Instant.class), anyString());
        verify(keycloak).endSession("rt");
        verify(auditRepo).record("user-1", "revoke", "127.0.0.1", "JUnit");
    }

    @Test
    void introspect_은_유효한_토큰의_경우_active_true_를_반환한다() {
        TulipUserPrincipal principal = new TulipUserPrincipal(
                "user-1", "demo", List.of("main"), "main",
                Set.of("LIBRARIAN"), Set.of(),
                "STAFF", null, "jti-1");
        when(jwtProvider.validateAndExtract("good")).thenReturn(principal);

        LoginDtos.IntrospectResponse resp = authService.introspect("good");

        assertThat(resp.active()).isTrue();
        assertThat(resp.sub()).isEqualTo("user-1");
        assertThat(resp.tenantId()).isEqualTo("demo");
        assertThat(resp.roles()).contains("LIBRARIAN");
    }
}
