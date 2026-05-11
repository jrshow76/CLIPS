package com.tulip.gateway.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.Set;

/**
 * API Gateway 보안·라우팅 속성.
 *
 * <p>{@code tulip.gateway.*} prefix.</p>
 */
@ConfigurationProperties(prefix = "tulip.gateway")
public record GatewayProperties(
        Security security
) {

    public record Security(
            String issuerUri,
            String jwksUri,
            Set<String> expectedAudiences,
            Set<String> publicPaths
    ) {
        public Security {
            if (expectedAudiences == null) {
                expectedAudiences = Set.of("admin-web", "opac-web", "iam-service", "account");
            }
            if (publicPaths == null) {
                publicPaths = Set.of(
                        "/actuator/health",
                        "/actuator/info",
                        "/api/v1/auth/login/initiate",
                        "/api/v1/auth/login/callback",
                        "/api/v1/auth/refresh",
                        "/api/v1/auth/logout",
                        "/v3/api-docs/**",
                        "/swagger-ui.html",
                        "/swagger-ui/**",
                        "/oauth2/**",
                        "/realms/**"
                );
            }
        }
    }
}
