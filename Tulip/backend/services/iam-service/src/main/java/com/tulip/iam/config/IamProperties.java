package com.tulip.iam.config;

import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.time.Duration;
import java.util.List;
import java.util.Set;

/**
 * IAM 서비스 설정값 바인딩.
 *
 * <p>{@code 05_security_and_auth.md} §2.4·§5.4 에 정의된 토큰 수명/audience/issuer 를 본 properties 로 외부화한다.
 * application.yml 의 {@code tulip.iam.*} prefix.</p>
 */
@Validated
@ConfigurationProperties(prefix = "tulip.iam")
public record IamProperties(
        Keycloak keycloak,
        Set<String> expectedAudiences,
        Cookie refreshCookie,
        Duration pkceTtl
) {

    public IamProperties {
        if (expectedAudiences == null) {
            expectedAudiences = Set.of("admin-web", "opac-web", "iam-service");
        }
        if (pkceTtl == null) {
            pkceTtl = Duration.ofMinutes(5);
        }
    }

    /** Keycloak 연결 설정. */
    public record Keycloak(
            @NotBlank String issuerUri,
            @NotBlank String authorizationEndpoint,
            @NotBlank String tokenEndpoint,
            @NotBlank String endSessionEndpoint,
            @NotBlank String jwksUri,
            @NotBlank String clientId,
            String clientSecret,
            String defaultRedirectUri,
            List<String> allowedRedirectUris
    ) {
    }

    /** Refresh Token HttpOnly Cookie 설정. */
    public record Cookie(
            String name,
            String path,
            String sameSite,
            boolean secure,
            Duration maxAge
    ) {
        public Cookie {
            if (name == null || name.isBlank()) {
                name = "tulip_rt";
            }
            if (path == null || path.isBlank()) {
                path = "/api/v1/auth";
            }
            if (sameSite == null || sameSite.isBlank()) {
                sameSite = "Lax";
            }
            if (maxAge == null) {
                maxAge = Duration.ofHours(12);
            }
        }
    }
}
