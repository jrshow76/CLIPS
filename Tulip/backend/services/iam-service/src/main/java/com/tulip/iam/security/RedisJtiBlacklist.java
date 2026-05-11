package com.tulip.iam.security;

import com.tulip.common.security.jwt.JtiBlacklistChecker;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;

/**
 * Redis 기반 JTI 블랙리스트 구현.
 *
 * <p>키 형식: {@code auth:jti:blacklist:{jti}}.
 * TTL 은 토큰 expiresAt - now 로 설정하여 자동 만료시킨다.</p>
 *
 * <p>{@code 05_security_and_auth.md} §2.5 — 로그아웃, 토큰 회전, 이상 탐지 시 차단.</p>
 */
@Component
public class RedisJtiBlacklist implements JtiBlacklistChecker {

    public static final String KEY_PREFIX = "auth:jti:blacklist:";
    private static final Duration MIN_TTL = Duration.ofSeconds(30);

    private final StringRedisTemplate redis;

    public RedisJtiBlacklist(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    public boolean isBlacklisted(String jti) {
        if (jti == null || jti.isBlank()) {
            return false;
        }
        Boolean has = redis.hasKey(KEY_PREFIX + jti);
        return Boolean.TRUE.equals(has);
    }

    /** jti 를 블랙리스트에 등록한다. */
    public void blacklist(String jti, Instant expiresAt, String reason) {
        if (jti == null || jti.isBlank()) {
            return;
        }
        Duration ttl = expiresAt == null
                ? Duration.ofHours(12)
                : Duration.between(Instant.now(), expiresAt);
        if (ttl.compareTo(MIN_TTL) < 0) {
            ttl = MIN_TTL;
        }
        redis.opsForValue().set(KEY_PREFIX + jti, reason == null ? "revoked" : reason, ttl);
    }
}
