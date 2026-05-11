package com.tulip.gateway.security;

import com.tulip.common.security.jwt.JtiBlacklistChecker;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

/**
 * Gateway 측 JTI 블랙리스트 구현 (Reactive Redis).
 *
 * <p>iam-service 와 동일한 키 스페이스({@code auth:jti:blacklist:*}) 를 공유하며,
 * iam-service 가 등록하고 Gateway 가 검증한다.</p>
 *
 * <p>{@link JtiBlacklistChecker} 인터페이스는 동기이므로 {@code hasKey()} 의 결과를
 * {@code block(timeout)} 하여 반환한다. JWT 검증 자체가 boundedElastic 스케줄러에서 실행되므로
 * 블로킹은 허용된다.</p>
 */
@Component
public class ReactiveRedisJtiBlacklist implements JtiBlacklistChecker {

    private static final String KEY_PREFIX = "auth:jti:blacklist:";
    private static final Duration TIMEOUT = Duration.ofMillis(200);

    private final ReactiveStringRedisTemplate redis;

    public ReactiveRedisJtiBlacklist(ReactiveStringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    public boolean isBlacklisted(String jti) {
        if (jti == null || jti.isBlank()) {
            return false;
        }
        Boolean has = redis.hasKey(KEY_PREFIX + jti).block(TIMEOUT);
        return Boolean.TRUE.equals(has);
    }
}
