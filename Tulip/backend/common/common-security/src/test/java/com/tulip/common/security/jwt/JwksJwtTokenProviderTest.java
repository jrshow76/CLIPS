package com.tulip.common.security.jwt;

import com.nimbusds.jose.JOSEObjectType;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.sun.net.httpserver.HttpServer;
import com.tulip.common.security.principal.TulipUserPrincipal;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.InetSocketAddress;
import java.util.Date;
import java.util.List;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link JwksJwtTokenProvider} 단위 테스트.
 *
 * <p>로컬 HTTP 서버에 JWKS 를 띄우고 자체 발급한 RS256 토큰을 검증한다.</p>
 */
class JwksJwtTokenProviderTest {

    private HttpServer jwksServer;
    private RSAKey rsaKey;
    private String issuer;
    private String jwksUri;

    @BeforeEach
    void setUp() throws Exception {
        rsaKey = new RSAKeyGenerator(2048).keyID("test-key").generate();
        JWKSet jwkSet = new JWKSet(rsaKey.toPublicJWK());
        String jwks = jwkSet.toString();

        jwksServer = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        jwksServer.createContext("/jwks", exchange -> {
            byte[] body = jwks.getBytes();
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        jwksServer.setExecutor(null);
        jwksServer.start();

        int port = jwksServer.getAddress().getPort();
        issuer = "http://127.0.0.1:" + port + "/realms/tulip";
        jwksUri = "http://127.0.0.1:" + port + "/jwks";
    }

    @AfterEach
    void tearDown() {
        if (jwksServer != null) {
            jwksServer.stop(0);
        }
    }

    @Test
    void validateAndExtract_원리적인_RS256_토큰을_principal_로_변환한다() throws Exception {
        String token = signToken(b -> b
                .issuer(issuer)
                .audience(List.of("admin-web"))
                .subject("user-001")
                .jwtID(UUID.randomUUID().toString())
                .issueTime(new Date())
                .expirationTime(new Date(System.currentTimeMillis() + 60_000))
                .claim("tenantId", "demo-tenant-1")
                .claim("branchIds", List.of("main", "east"))
                .claim("roles", List.of("LIBRARIAN"))
                .claim("scope", "openid profile cir:read"));

        JwksJwtTokenProvider provider = new JwksJwtTokenProvider(jwksUri, issuer, Set.of("admin-web"));
        TulipUserPrincipal principal = provider.validateAndExtract(token);

        assertThat(principal.userId()).isEqualTo("user-001");
        assertThat(principal.tenantId()).isEqualTo("demo-tenant-1");
        assertThat(principal.libraryIds()).containsExactly("main", "east");
        assertThat(principal.roles()).contains("LIBRARIAN");
        assertThat(principal.scopes()).contains("openid", "profile", "cir:read");
    }

    @Test
    void validateAndExtract_audience_가_일치하지_않으면_예외() throws Exception {
        String token = signToken(b -> b
                .issuer(issuer)
                .audience(List.of("opac-web"))
                .subject("user-002")
                .jwtID(UUID.randomUUID().toString())
                .issueTime(new Date())
                .expirationTime(new Date(System.currentTimeMillis() + 60_000))
                .claim("tenantId", "demo-tenant-1"));

        JwksJwtTokenProvider provider = new JwksJwtTokenProvider(jwksUri, issuer, Set.of("admin-web"));
        assertThatThrownBy(() -> provider.validateAndExtract(token))
                .isInstanceOf(JwksJwtTokenProvider.InvalidJwtException.class);
    }

    @Test
    void validateAndExtract_만료된_토큰은_예외() throws Exception {
        String token = signToken(b -> b
                .issuer(issuer)
                .audience(List.of("admin-web"))
                .subject("user-003")
                .jwtID(UUID.randomUUID().toString())
                .issueTime(new Date(System.currentTimeMillis() - 120_000))
                .expirationTime(new Date(System.currentTimeMillis() - 60_000))
                .claim("tenantId", "demo-tenant-1"));

        JwksJwtTokenProvider provider = new JwksJwtTokenProvider(jwksUri, issuer, Set.of("admin-web"));
        assertThatThrownBy(() -> provider.validateAndExtract(token))
                .isInstanceOf(JwksJwtTokenProvider.InvalidJwtException.class);
    }

    private String signToken(java.util.function.UnaryOperator<JWTClaimsSet.Builder> build) throws Exception {
        JWTClaimsSet claims = build.apply(new JWTClaimsSet.Builder()).build();
        SignedJWT jwt = new SignedJWT(
                new JWSHeader.Builder(JWSAlgorithm.RS256)
                        .type(JOSEObjectType.JWT)
                        .keyID(rsaKey.getKeyID())
                        .build(),
                claims);
        jwt.sign(new RSASSASigner(rsaKey));
        return jwt.serialize();
    }
}
