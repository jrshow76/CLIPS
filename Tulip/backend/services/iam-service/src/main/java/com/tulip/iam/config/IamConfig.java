package com.tulip.iam.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.security.handler.TulipAccessDeniedHandler;
import com.tulip.common.security.handler.TulipAuthenticationEntryPoint;
import com.tulip.common.security.jwt.JwksJwtTokenProvider;
import com.tulip.common.security.jwt.JwtTokenProvider;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import com.tulip.iam.security.IamBearerAuthenticationFilter;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/**
 * IAM 서비스 보안·인프라 설정.
 *
 * <p>iam-service 자체도 Resource Server 이지만, 로그인/콜백/리프레시 엔드포인트는
 * 인증이 필요 없으므로 별도 화이트리스트로 처리한다.</p>
 */
@Configuration
@EnableConfigurationProperties(IamProperties.class)
public class IamConfig {

    @Bean
    public JwtTokenProvider jwtTokenProvider(IamProperties props) {
        return new JwksJwtTokenProvider(
                props.keycloak().jwksUri(),
                props.keycloak().issuerUri(),
                props.expectedAudiences()
        );
    }

    @Bean
    public StringRedisTemplate stringRedisTemplate(RedisConnectionFactory connectionFactory) {
        return new StringRedisTemplate(connectionFactory);
    }

    @Bean
    public RestTemplate keycloakRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout((int) Duration.ofSeconds(3).toMillis());
        factory.setReadTimeout((int) Duration.ofSeconds(5).toMillis());
        return new RestTemplate(factory);
    }

    @Bean
    public TulipAuthenticationEntryPoint authenticationEntryPoint(ObjectMapper objectMapper) {
        return new TulipAuthenticationEntryPoint(objectMapper);
    }

    @Bean
    public TulipAccessDeniedHandler accessDeniedHandler(ObjectMapper objectMapper) {
        return new TulipAccessDeniedHandler(objectMapper);
    }

    /**
     * IAM 서비스 Security 체인.
     *
     * <p>BFF 엔드포인트(/api/v1/auth/login/**, /refresh, /logout) 는 익명 허용.
     * /me, /introspect, /mfa/** 는 인증 필요.</p>
     */
    @Bean
    @org.springframework.core.annotation.Order(org.springframework.core.Ordered.HIGHEST_PRECEDENCE + 10)
    public SecurityFilterChain iamSecurityFilterChain(
            HttpSecurity http,
            TulipAuthenticationEntryPoint entryPoint,
            TulipAccessDeniedHandler deniedHandler,
            IamBearerAuthenticationFilter bearerFilter
    ) throws Exception {
        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(AbstractHttpConfigurer::disable) // CORS 는 Gateway 에서 처리
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(
                                "/actuator/health/**",
                                "/actuator/info",
                                "/v3/api-docs/**",
                                "/swagger-ui.html",
                                "/swagger-ui/**",
                                "/api/v1/auth/login/initiate",
                                "/api/v1/auth/login/callback",
                                "/api/v1/auth/refresh",
                                "/api/v1/auth/logout"
                        ).permitAll()
                        .anyRequest().authenticated()
                )
                // 본 모듈은 Bearer 토큰 검증을 별도 AuthFilter 로 처리한다.
                .addFilterBefore(bearerFilter, UsernamePasswordAuthenticationFilter.class)
                .exceptionHandling(eh -> eh
                        .authenticationEntryPoint(entryPoint)
                        .accessDeniedHandler(deniedHandler));

        return http.build();
    }
}
