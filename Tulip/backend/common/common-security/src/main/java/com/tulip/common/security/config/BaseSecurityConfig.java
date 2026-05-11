package com.tulip.common.security.config;

import org.springframework.context.annotation.Bean;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

/**
 * Tulip+ 모든 마이크로서비스가 상속/임포트하여 사용하는 보안 기반 설정.
 *
 * <p>기본 정책: CSRF 비활성(Stateless JWT), Stateless 세션, 화이트리스트 외 인증 요구.
 * 각 서비스는 본 클래스를 상속하여 endpoint 별 권한 규칙을 추가한다.
 * 정책 근거는 {@code 05_security_and_auth.md} §6 (API 보안).</p>
 */
public abstract class BaseSecurityConfig {

    /** 공개 경로 화이트리스트 (각 서비스가 override 가능). */
    protected String[] publicPaths() {
        return new String[]{
                "/actuator/health",
                "/actuator/info",
                "/v3/api-docs/**",
                "/swagger-ui.html",
                "/swagger-ui/**"
        };
    }

    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE + 50)
    public SecurityFilterChain tulipSecurityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                        .requestMatchers(publicPaths()).permitAll()
                        .anyRequest().authenticated()
                );
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        // 운영 환경은 화이트리스트로 override (05_security_and_auth.md §6.3)
        config.setAllowedOrigins(List.of("*"));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"));
        config.setAllowedHeaders(List.of("*"));
        config.setExposedHeaders(List.of(
                "X-Trace-Id", "traceparent", "ETag", "Location",
                "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"));
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}
