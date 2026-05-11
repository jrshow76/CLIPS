package com.tulip.member.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.security.config.BaseSecurityConfig;
import com.tulip.common.security.handler.TulipAccessDeniedHandler;
import com.tulip.common.security.handler.TulipAuthenticationEntryPoint;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

/**
 * member-service 보안 체인.
 *
 * <p>모든 {@code /api/v1/members/**} 는 JWT 인증 필수. 메서드 단위 {@code @PreAuthorize} 로 역할 제어.</p>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class MemberSecurityConfig extends BaseSecurityConfig {

    @Bean
    public TulipAuthenticationEntryPoint memberAuthEntryPoint(ObjectMapper objectMapper) {
        return new TulipAuthenticationEntryPoint(objectMapper);
    }

    @Bean
    public TulipAccessDeniedHandler memberAccessDeniedHandler(ObjectMapper objectMapper) {
        return new TulipAccessDeniedHandler(objectMapper);
    }

    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE + 20)
    public SecurityFilterChain memberSecurityFilterChain(
            HttpSecurity http,
            MemberBearerAuthenticationFilter bearerFilter,
            TulipAuthenticationEntryPoint entryPoint,
            TulipAccessDeniedHandler deniedHandler
    ) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                        .requestMatchers(publicPaths()).permitAll()
                        .anyRequest().authenticated())
                .addFilterBefore(bearerFilter, UsernamePasswordAuthenticationFilter.class)
                .exceptionHandling(eh -> eh
                        .authenticationEntryPoint(entryPoint)
                        .accessDeniedHandler(deniedHandler));
        return http.build();
    }
}
