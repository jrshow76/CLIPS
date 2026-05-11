package com.tulip.codepolicy.security;

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
 * code-policy-service 보안 체인.
 *
 * <p>{@code /api/v1/codes/groups/**} GET 은 모든 인증된 사용자에게 허용 (글로벌 코드 참조용).
 * 변경(POST/PATCH/DELETE) 및 정책은 메서드별 {@code @PreAuthorize} 로 권한 강제.</p>
 */
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class CodePolicySecurityConfig extends BaseSecurityConfig {

    @Bean
    public TulipAuthenticationEntryPoint codePolicyAuthEntryPoint(ObjectMapper objectMapper) {
        return new TulipAuthenticationEntryPoint(objectMapper);
    }

    @Bean
    public TulipAccessDeniedHandler codePolicyAccessDeniedHandler(ObjectMapper objectMapper) {
        return new TulipAccessDeniedHandler(objectMapper);
    }

    @Bean
    @Order(Ordered.HIGHEST_PRECEDENCE + 20)
    public SecurityFilterChain codePolicySecurityFilterChain(
            HttpSecurity http,
            CodePolicyBearerAuthenticationFilter bearerFilter,
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
