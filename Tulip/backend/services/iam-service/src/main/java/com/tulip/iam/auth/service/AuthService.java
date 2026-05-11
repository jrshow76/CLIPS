package com.tulip.iam.auth.service;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.security.error.AuthErrorCode;
import com.tulip.common.security.jwt.JwtTokenProvider;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.iam.auth.dto.LoginDtos;
import com.tulip.iam.auth.repository.IamRefreshAuditRepository;
import com.tulip.iam.auth.repository.IamUserLinkRepository;
import com.tulip.iam.config.IamProperties;
import com.tulip.iam.keycloak.KeycloakClient;
import com.tulip.iam.security.PkceStateStore;
import com.tulip.iam.security.RedisJtiBlacklist;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;
import java.util.UUID;

/**
 * Tulip+ IAM 인증 흐름의 핵심 서비스.
 *
 * <p>{@code 05_security_and_auth.md} §2.2 의 OAuth2 Authorization Code + PKCE 흐름을 BFF 패턴으로 구현한다.</p>
 */
@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final Base64.Encoder BASE64URL = Base64.getUrlEncoder().withoutPadding();

    private final IamProperties props;
    private final PkceStateStore pkceStore;
    private final KeycloakClient keycloak;
    private final JwtTokenProvider jwtProvider;
    private final RedisJtiBlacklist blacklist;
    private final IamUserLinkRepository userLinkRepository;
    private final IamRefreshAuditRepository refreshAuditRepository;

    public AuthService(IamProperties props,
                       PkceStateStore pkceStore,
                       KeycloakClient keycloak,
                       JwtTokenProvider jwtProvider,
                       RedisJtiBlacklist blacklist,
                       IamUserLinkRepository userLinkRepository,
                       IamRefreshAuditRepository refreshAuditRepository) {
        this.props = props;
        this.pkceStore = pkceStore;
        this.keycloak = keycloak;
        this.jwtProvider = jwtProvider;
        this.blacklist = blacklist;
        this.userLinkRepository = userLinkRepository;
        this.refreshAuditRepository = refreshAuditRepository;
    }

    /* ============================== Login Initiate ============================== */

    public LoginDtos.InitiateResponse initiate(LoginDtos.InitiateRequest req) {
        String state = newRandom(24);
        String codeVerifier = newRandom(48);
        String codeChallenge = sha256Base64Url(codeVerifier);
        String redirectUri = props.keycloak().defaultRedirectUri();
        pkceStore.put(state, codeVerifier, redirectUri);

        String authorizeUrl = props.keycloak().authorizationEndpoint()
                + "?response_type=code"
                + "&client_id=" + enc(props.keycloak().clientId())
                + "&redirect_uri=" + enc(redirectUri)
                + "&state=" + enc(state)
                + "&scope=" + enc("openid profile email")
                + "&code_challenge=" + enc(codeChallenge)
                + "&code_challenge_method=S256";
        return new LoginDtos.InitiateResponse(authorizeUrl, state, codeChallenge, "S256");
    }

    /* ============================== Login Callback ============================== */

    public TokenExchangeResult callback(LoginDtos.CallbackRequest req, String clientIp, String userAgent) {
        PkceStateStore.PkceEntry entry = pkceStore.consume(req.state());
        if (entry == null) {
            throw new BusinessException(AuthErrorCode.TOKEN_INVALID, "state 가 만료되었거나 유효하지 않습니다");
        }
        String redirectUri = entry.redirectUri() != null ? entry.redirectUri() : props.keycloak().defaultRedirectUri();
        Map<String, Object> tokenResp = keycloak.exchangeCode(req.code(), redirectUri, entry.codeVerifier());

        String accessToken = stringOf(tokenResp, "access_token");
        String refreshToken = stringOf(tokenResp, "refresh_token");
        long expiresIn = longOf(tokenResp, "expires_in");
        String scope = stringOf(tokenResp, "scope");

        TulipUserPrincipal principal = jwtProvider.validateAndExtract(accessToken);
        ensureUserLink(principal);
        refreshAuditRepository.record(principal.userId(), "issue", clientIp, userAgent);

        return new TokenExchangeResult(principal, accessToken, refreshToken, expiresIn, scope);
    }

    /* ============================== Refresh Rotation ============================== */

    public TokenExchangeResult rotateRefresh(String refreshToken, String clientIp, String userAgent) {
        if (refreshToken == null || refreshToken.isBlank()) {
            throw new BusinessException(AuthErrorCode.TOKEN_MISSING, "Refresh Token 쿠키가 없습니다");
        }
        // 구 Refresh JTI 블랙리스트 등록 (재사용 탐지)
        String oldJti = jwtProvider.tokenId(refreshToken);
        Map<String, Object> resp = keycloak.refresh(refreshToken);
        String newAccess = stringOf(resp, "access_token");
        String newRefresh = stringOf(resp, "refresh_token");
        long expiresIn = longOf(resp, "expires_in");
        String scope = stringOf(resp, "scope");

        TulipUserPrincipal principal = jwtProvider.validateAndExtract(newAccess);

        if (oldJti != null) {
            // refresh 의 정확한 exp 는 알 수 없으나 보수적으로 12h TTL
            blacklist.blacklist(oldJti, Instant.now().plusSeconds(12 * 3600), "rotated");
        }
        refreshAuditRepository.record(principal.userId(), "rotate", clientIp, userAgent);
        return new TokenExchangeResult(principal, newAccess, newRefresh, expiresIn, scope);
    }

    /* ============================== Logout ============================== */

    public void logout(String accessToken, String refreshToken, String clientIp, String userAgent) {
        if (accessToken != null) {
            String jti = jwtProvider.tokenId(accessToken);
            if (jti != null) {
                blacklist.blacklist(jti, Instant.now().plusSeconds(3600), "logout");
            }
            TulipUserPrincipal principal;
            try {
                principal = jwtProvider.validateAndExtract(accessToken);
                refreshAuditRepository.record(principal.userId(), "revoke", clientIp, userAgent);
            } catch (Exception ignored) {
                // 토큰이 이미 만료 → 무시
            }
        }
        if (refreshToken != null) {
            String rJti = jwtProvider.tokenId(refreshToken);
            if (rJti != null) {
                blacklist.blacklist(rJti, Instant.now().plusSeconds(12 * 3600), "logout");
            }
            keycloak.endSession(refreshToken);
        }
    }

    /* ============================== Introspect ============================== */

    public LoginDtos.IntrospectResponse introspect(String token) {
        try {
            TulipUserPrincipal p = jwtProvider.validateAndExtract(token);
            return new LoginDtos.IntrospectResponse(
                    true,
                    p.userId(),
                    p.tenantId(),
                    p.libraryIds(),
                    p.roles() == null ? java.util.List.of() : p.roles().stream().toList(),
                    p.tokenId(),
                    null
            );
        } catch (Exception ex) {
            return new LoginDtos.IntrospectResponse(false, null, null, java.util.List.of(), java.util.List.of(), null, null);
        }
    }

    /* ============================== User Link Sync ============================== */

    private void ensureUserLink(TulipUserPrincipal principal) {
        if (principal == null || principal.userId() == null) {
            return;
        }
        userLinkRepository.upsert(
                principal.userId(),         // user_id (내부)
                principal.userId(),         // kc_sub (Keycloak sub) - 본 구현에서는 동일
                principal.tenantId(),
                principal.primaryLibraryId()
        );
    }

    /* ============================== Utility ============================== */

    private static String newRandom(int byteLen) {
        byte[] buf = new byte[byteLen];
        RANDOM.nextBytes(buf);
        return BASE64URL.encodeToString(buf);
    }

    private static String sha256Base64Url(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(input.getBytes(StandardCharsets.US_ASCII));
            return BASE64URL.encodeToString(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 미지원", e);
        }
    }

    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8);
    }

    private static String stringOf(Map<String, Object> map, String key) {
        Object v = map.get(key);
        return v == null ? null : String.valueOf(v);
    }

    private static long longOf(Map<String, Object> map, String key) {
        Object v = map.get(key);
        if (v == null) return 0L;
        if (v instanceof Number n) return n.longValue();
        try { return Long.parseLong(String.valueOf(v)); } catch (NumberFormatException e) { return 0L; }
    }

    /** 토큰 교환 결과 묶음. */
    public record TokenExchangeResult(
            TulipUserPrincipal principal,
            String accessToken,
            String refreshToken,
            long expiresIn,
            String scope
    ) {
    }

    /** 외부에서 새 UUID 형 jti 가 필요한 경우. */
    public static String newJti() {
        return UUID.randomUUID().toString();
    }
}
