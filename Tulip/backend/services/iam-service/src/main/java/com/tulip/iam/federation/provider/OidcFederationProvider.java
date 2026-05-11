package com.tulip.iam.federation.provider;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * OpenID Connect(OIDC) 외부 IdP 연동 어댑터 (Phase 1-B 스텁).
 *
 * <p>학교·기관 SSO 의 2차 프로토콜로 OIDC 를 지원한다. Phase 3 에서
 * Spring Security OAuth2 Client 를 통해 authorization code + PKCE 플로우를
 * 구현하고, ID Token 의 서명·issuer·audience 검증을 수행한다.</p>
 *
 * <p>활성화 조건: {@code tulip.federation.oidc.enabled=true}.</p>
 */
@Component
@ConditionalOnProperty(prefix = "tulip.federation.oidc", name = "enabled", havingValue = "true", matchIfMissing = false)
public class OidcFederationProvider extends AbstractStubFederationProvider {

    /** 어댑터 타입 상수. */
    public static final String TYPE = "OIDC";

    /** 기본 providerId (테넌트별 다수 등록 시 등록 데이터 기준으로 덮어쓴다). */
    public static final String DEFAULT_PROVIDER_ID = "oidc-default";

    @Override
    public String type() {
        return TYPE;
    }

    @Override
    public String providerId() {
        return DEFAULT_PROVIDER_ID;
    }
}
