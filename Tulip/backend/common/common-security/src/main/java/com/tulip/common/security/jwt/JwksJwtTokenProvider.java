package com.tulip.common.security.jwt;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.proc.BadJOSEException;
import com.nimbusds.jose.proc.JWSKeySelector;
import com.nimbusds.jose.proc.JWSVerificationKeySelector;
import com.nimbusds.jose.proc.SecurityContext;
import com.nimbusds.jose.proc.SimpleSecurityContext;
import com.nimbusds.jwt.JWT;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.JWTParser;
import com.nimbusds.jwt.proc.BadJWTException;
import com.nimbusds.jwt.proc.ConfigurableJWTProcessor;
import com.nimbusds.jwt.proc.DefaultJWTClaimsVerifier;
import com.nimbusds.jwt.proc.DefaultJWTProcessor;
import com.tulip.common.security.principal.TulipUserPrincipal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.text.ParseException;
import java.time.Duration;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Keycloak JWKS 기반 JWT 검증기 (RS256).
 *
 * <p>{@code 05_security_and_auth.md} §2.5 의 표준을 따른다.</p>
 * <ul>
 *   <li>JWKS URI를 주기적으로 가져와 메모리 캐시(기본 1시간)에 보관.</li>
 *   <li>iss·aud·exp·nbf 표준 클레임 검증.</li>
 *   <li>tenantId·branchIds·roles·scopes 등 커스텀 클레임을 {@link TulipUserPrincipal} 로 추출.</li>
 *   <li>JWKS 의 kid 미스매치 시 1회 강제 refresh 후 재시도.</li>
 * </ul>
 *
 * <p>본 구현체는 servlet/reactive 양쪽에서 공통 사용 가능하도록 동기 HttpClient 만 사용한다.</p>
 */
public class JwksJwtTokenProvider implements JwtTokenProvider {

    private static final Logger log = LoggerFactory.getLogger(JwksJwtTokenProvider.class);

    private final URI jwksUri;
    private final String issuer;
    private final Set<String> expectedAudiences;
    private final Duration cacheTtl;
    private final HttpClient httpClient;

    /** JWKSet 캐시 (atomic swap). */
    private final AtomicReference<CachedJwks> cachedRef = new AtomicReference<>();

    public JwksJwtTokenProvider(String jwksUri, String issuer, Set<String> expectedAudiences) {
        this(URI.create(jwksUri), issuer, expectedAudiences, Duration.ofHours(1));
    }

    public JwksJwtTokenProvider(URI jwksUri, String issuer, Set<String> expectedAudiences, Duration cacheTtl) {
        this.jwksUri = jwksUri;
        this.issuer = issuer;
        this.expectedAudiences = expectedAudiences == null ? Set.of() : Set.copyOf(expectedAudiences);
        this.cacheTtl = cacheTtl == null ? Duration.ofHours(1) : cacheTtl;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
    }

    @Override
    public TulipUserPrincipal validateAndExtract(String token) {
        try {
            JWTClaimsSet claims = processAndVerify(token);
            return toPrincipal(claims);
        } catch (BadJOSEException | JOSEException | ParseException e) {
            throw new InvalidJwtException("JWT 검증 실패", e);
        }
    }

    @Override
    public boolean isExpired(String token) {
        try {
            JWT jwt = JWTParser.parse(token);
            Date exp = jwt.getJWTClaimsSet().getExpirationTime();
            return exp != null && exp.before(new Date());
        } catch (ParseException e) {
            return true;
        }
    }

    @Override
    public String tokenId(String token) {
        try {
            return JWTParser.parse(token).getJWTClaimsSet().getJWTID();
        } catch (ParseException e) {
            return null;
        }
    }

    /* ============================== 내부 구현 ============================== */

    private JWTClaimsSet processAndVerify(String token) throws BadJOSEException, JOSEException, ParseException {
        ConfigurableJWTProcessor<SecurityContext> processor = newProcessor(getOrLoadJwks().jwks());
        try {
            return processor.process(token, new SimpleSecurityContext());
        } catch (BadJOSEException retry) {
            // kid 미스매치 등 — 강제 refresh 후 1회 재시도
            log.debug("JWT 검증 실패 — JWKS 강제 갱신 후 재시도 cause={}", retry.getMessage());
            JWKSet fresh = forceRefreshJwks();
            ConfigurableJWTProcessor<SecurityContext> p2 = newProcessor(fresh);
            return p2.process(token, new SimpleSecurityContext());
        }
    }

    private ConfigurableJWTProcessor<SecurityContext> newProcessor(JWKSet jwks) {
        DefaultJWTProcessor<SecurityContext> processor = new DefaultJWTProcessor<>();
        JWSKeySelector<SecurityContext> selector = new JWSVerificationKeySelector<>(
                JWSAlgorithm.RS256,
                (jwkSelector, ctx) -> jwkSelector.select(jwks)
        );
        processor.setJWSKeySelector(selector);

        Set<String> required = new HashSet<>(Set.of("sub", "exp", "iat", "iss"));
        processor.setJWTClaimsSetVerifier(new DefaultJWTClaimsVerifier<>(
                new JWTClaimsSet.Builder().issuer(issuer).build(),
                required
        ) {
            @Override
            public void verify(JWTClaimsSet claims, SecurityContext context) throws BadJWTException {
                super.verify(claims, context);
                // audience 검증 — Keycloak 는 aud 가 client id 인 경우와 account 인 경우가 혼재되므로
                // expectedAudiences 가 비어있지 않으면 교집합 검사.
                if (!expectedAudiences.isEmpty()) {
                    List<String> aud = claims.getAudience();
                    if (aud == null || aud.stream().noneMatch(expectedAudiences::contains)) {
                        throw new BadJWTException("aud 클레임 검증 실패: expected one of " + expectedAudiences);
                    }
                }
            }
        });
        return processor;
    }

    private CachedJwks getOrLoadJwks() throws JOSEException {
        CachedJwks cached = cachedRef.get();
        long now = System.currentTimeMillis();
        if (cached != null && now < cached.expiresAtMillis()) {
            return cached;
        }
        return forceRefresh(now);
    }

    private JWKSet forceRefreshJwks() throws JOSEException {
        return forceRefresh(System.currentTimeMillis()).jwks();
    }

    private synchronized CachedJwks forceRefresh(long now) throws JOSEException {
        // double-check after lock
        CachedJwks cached = cachedRef.get();
        if (cached != null && now < cached.expiresAtMillis() && cached.fetchedAtMillis() > now - 5_000) {
            return cached;
        }
        try {
            HttpResponse<String> resp = httpClient.send(
                    HttpRequest.newBuilder(jwksUri).timeout(Duration.ofSeconds(5)).GET().build(),
                    HttpResponse.BodyHandlers.ofString()
            );
            if (resp.statusCode() / 100 != 2) {
                throw new JOSEException("JWKS 응답 비정상 status=" + resp.statusCode());
            }
            JWKSet parsed = JWKSet.parse(resp.body());
            CachedJwks fresh = new CachedJwks(parsed, now, now + cacheTtl.toMillis());
            cachedRef.set(fresh);
            log.info("JWKS 캐시 갱신 keys={} ttl={}s", parsed.getKeys().size(), cacheTtl.toSeconds());
            return fresh;
        } catch (Exception e) {
            throw new JOSEException("JWKS 조회 실패: " + jwksUri, e);
        }
    }

    @SuppressWarnings("unchecked")
    private static TulipUserPrincipal toPrincipal(JWTClaimsSet claims) {
        Set<String> roles = stringSet(claims.getClaim("roles"));
        // Keycloak realm_access.roles fallback
        if (roles.isEmpty()) {
            Object realmAccess = claims.getClaim("realm_access");
            if (realmAccess instanceof java.util.Map<?, ?> m) {
                Object r = m.get("roles");
                if (r instanceof List<?> list) {
                    list.forEach(x -> roles.add(String.valueOf(x)));
                }
            }
        }
        Set<String> scopes = stringSet(claims.getClaim("scopes"));
        if (scopes.isEmpty()) {
            Object scope = claims.getClaim("scope");
            if (scope instanceof String s) {
                for (String tok : s.split("\\s+")) {
                    if (!tok.isBlank()) {
                        scopes.add(tok);
                    }
                }
            }
        }

        List<String> libraryIds = stringList(claims.getClaim("libraryIds"));
        if (libraryIds.isEmpty()) {
            libraryIds = stringList(claims.getClaim("branchIds"));
        }

        String tenantId = stringClaim(claims, "tenantId");
        String primaryBranchId = stringClaim(claims, "primaryBranchId");
        String memberType = stringClaim(claims, "memberType");
        String deviceId = stringClaim(claims, "deviceId");

        return new TulipUserPrincipal(
                claims.getSubject(),
                tenantId,
                libraryIds,
                primaryBranchId,
                roles,
                scopes,
                memberType,
                deviceId,
                claims.getJWTID()
        );
    }

    private static Set<String> stringSet(Object claim) {
        Set<String> out = new HashSet<>();
        if (claim instanceof List<?> list) {
            list.forEach(o -> out.add(String.valueOf(o)));
        }
        return out;
    }

    private static List<String> stringList(Object claim) {
        if (claim instanceof List<?> list) {
            return list.stream().map(String::valueOf).toList();
        }
        return List.of();
    }

    private static String stringClaim(JWTClaimsSet claims, String key) {
        Object v = claims.getClaim(key);
        return v == null ? null : String.valueOf(v);
    }

    /** JWKS 캐시 엔트리. */
    private record CachedJwks(JWKSet jwks, long fetchedAtMillis, long expiresAtMillis) {
    }

    /** JWT 검증 실패 표준 예외 (호출부가 401 매핑). */
    public static class InvalidJwtException extends RuntimeException {
        public InvalidJwtException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
