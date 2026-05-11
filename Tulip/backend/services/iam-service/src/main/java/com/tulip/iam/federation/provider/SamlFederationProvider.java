package com.tulip.iam.federation.provider;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * SAML 2.0 외부 IdP 연동 어댑터 (Phase 1-B 스텁).
 *
 * <p>학교·기관 SSO 의 1차 프로토콜로 SAML 2.0 을 지원한다.
 * Phase 1-B 시점에는 모든 호출에서 {@code TLP-AUT-FED-501} 을 던지며,
 * Phase 3 에서 OpenSAML 등 라이브러리를 채택해 AuthnRequest 생성·
 * Assertion 서명 검증을 구현한다.</p>
 *
 * <p>활성화 조건: {@code tulip.federation.saml.enabled=true}.</p>
 */
@Component
@ConditionalOnProperty(prefix = "tulip.federation.saml", name = "enabled", havingValue = "true", matchIfMissing = false)
public class SamlFederationProvider extends AbstractStubFederationProvider {

    /** 어댑터 타입 상수. */
    public static final String TYPE = "SAML";

    /** 기본 providerId (테넌트별 다수 등록 시 등록 데이터 기준으로 덮어쓴다). */
    public static final String DEFAULT_PROVIDER_ID = "saml-default";

    @Override
    public String type() {
        return TYPE;
    }

    @Override
    public String providerId() {
        return DEFAULT_PROVIDER_ID;
    }
}
