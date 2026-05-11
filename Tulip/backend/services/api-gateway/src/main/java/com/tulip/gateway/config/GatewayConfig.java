package com.tulip.gateway.config;

import com.tulip.common.security.jwt.JwksJwtTokenProvider;
import com.tulip.common.security.jwt.JwtTokenProvider;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

import java.net.InetSocketAddress;

/**
 * Gateway 인프라 빈 정의.
 *
 * <p>JWT 검증기·Rate Limiter 키 리졸버·Redis Rate Limiter 빈을 등록한다.</p>
 */
@Configuration
@EnableConfigurationProperties(GatewayProperties.class)
public class GatewayConfig {

    @Bean
    public JwtTokenProvider jwtTokenProvider(GatewayProperties props) {
        return new JwksJwtTokenProvider(
                props.security().jwksUri(),
                props.security().issuerUri(),
                props.security().expectedAudiences()
        );
    }

    /** 익명 트래픽용 IP 기반 KeyResolver. */
    @Bean("anonymousKeyResolver")
    public KeyResolver anonymousKeyResolver() {
        return exchange -> {
            InetSocketAddress remote = exchange.getRequest().getRemoteAddress();
            String ip = remote != null ? remote.getAddress().getHostAddress() : "unknown";
            String xff = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
            if (xff != null && !xff.isBlank()) {
                ip = xff.split(",")[0].trim();
            }
            return Mono.just("anon:" + ip);
        };
    }

    /** 인증 사용자용 KeyResolver (X-User-Id 기반 — JwtAuthenticationFilter 통과 후 부착). */
    @Bean("userKeyResolver")
    public KeyResolver userKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
            if (userId != null && !userId.isBlank()) {
                return Mono.just("user:" + userId);
            }
            // fallback to IP
            InetSocketAddress remote = exchange.getRequest().getRemoteAddress();
            String ip = remote != null ? remote.getAddress().getHostAddress() : "unknown";
            return Mono.just("anon:" + ip);
        };
    }

    /** Redis Rate Limiter — replenishRate=300/min(=5/s), burstCapacity=10. */
    @Bean
    public RedisRateLimiter redisRateLimiter() {
        // 300 req/min ≈ 5 req/s
        return new RedisRateLimiter(5, 10);
    }
}
