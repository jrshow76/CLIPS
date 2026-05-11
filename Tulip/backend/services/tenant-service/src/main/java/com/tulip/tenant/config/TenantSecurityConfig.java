package com.tulip.tenant.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.security.handler.TulipAccessDeniedHandler;
import com.tulip.common.security.handler.TulipAuthenticationEntryPoint;
import com.tulip.common.security.jwt.JwksJwtTokenProvider;
import com.tulip.common.security.jwt.JwtTokenProvider;
import com.tulip.tenant.security.TenantAuthFilter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * tenant-service 보안 설정.
 *
 * <p>common-security 의 베이스를 상속하지 않고 명시적으로 구성한다 (다른 서비스보다
 * RLS · Bypass 요구사항이 강하므로 가시성을 우선시함).</p>
 */
@Configuration
@EnableMethodSecurity(prePostEnabled = true)
public class TenantSecurityConfig {

    @Value("${tulip.tenant.keycloak.issuer-uri}")
    private String issuerUri;

    @Value("${tulip.tenant.keycloak.jwks-uri}")
    private String jwksUri;

    @Value("${tulip.tenant.expected-audiences:tenant-service,admin-web}")
    private List<String> expectedAudiences;

    @Bean
    public JwtTokenProvider jwtTokenProvider() {
        Set<String> aud = new LinkedHashSet<>(expectedAudiences);
        return new JwksJwtTokenProvider(jwksUri, issuerUri, aud);
    }

    @Bean
    public TulipAuthenticationEntryPoint authenticationEntryPoint(ObjectMapper om) {
        return new TulipAuthenticationEntryPoint(om);
    }

    @Bean
    public TulipAccessDeniedHandler accessDeniedHandler(ObjectMapper om) {
        return new TulipAccessDeniedHandler(om);
    }

    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE + 10)
    public SecurityFilterChain tenantSecurityFilterChain(
            HttpSecurity http,
            TenantAuthFilter authFilter,
            TulipAuthenticationEntryPoint entryPoint,
            TulipAccessDeniedHandler deniedHandler
    ) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(
                                "/actuator/health/**",
                                "/actuator/info",
                                "/v3/api-docs/**",
                                "/swagger-ui.html",
                                "/swagger-ui/**"
                        ).permitAll()
                        .anyRequest().authenticated()
                )
                .addFilterBefore(authFilter, UsernamePasswordAuthenticationFilter.class)
                .exceptionHandling(eh -> eh
                        .authenticationEntryPoint(entryPoint)
                        .accessDeniedHandler(deniedHandler));
        return http.build();
    }
}
