package com.tulip.iam.security;

import com.tulip.iam.config.IamProperties;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

/**
 * PKCE state/code_verifier 임시 저장소(Redis).
 *
 * <p>키 형식: {@code auth:pkce:state:{state}}.
 * 값: {@code code_verifier}|{redirect_uri}. TTL 은 properties 에서 결정(기본 5분).</p>
 */
@Component
public class PkceStateStore {

    public static final String KEY_PREFIX = "auth:pkce:state:";

    private final StringRedisTemplate redis;
    private final IamProperties props;

    public PkceStateStore(StringRedisTemplate redis, IamProperties props) {
        this.redis = redis;
        this.props = props;
    }

    public void put(String state, String codeVerifier, String redirectUri) {
        String value = (redirectUri == null ? "" : redirectUri) + "|" + codeVerifier;
        redis.opsForValue().set(KEY_PREFIX + state, value, props.pkceTtl());
    }

    /** state 를 소비(GETDEL)하여 {redirectUri, codeVerifier} 를 반환한다. */
    public PkceEntry consume(String state) {
        String key = KEY_PREFIX + state;
        String raw = redis.opsForValue().getAndDelete(key);
        if (raw == null) {
            return null;
        }
        int idx = raw.indexOf('|');
        if (idx < 0) {
            return new PkceEntry(null, raw);
        }
        return new PkceEntry(raw.substring(0, idx), raw.substring(idx + 1));
    }

    public record PkceEntry(String redirectUri, String codeVerifier) {
    }
}
