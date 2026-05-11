package com.tulip.iam.federation.provider;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * LDAP / Active Directory 연동 어댑터 (Phase 1-B 스텁).
 *
 * <p>대학 직원 디렉토리 fallback 인증으로 사용된다.
 * Phase 3 에서 Spring LDAP 또는 UnboundID SDK 를 통해 StartTLS 기반
 * bind/search 인증을 구현한다.</p>
 *
 * <p>활성화 조건: {@code tulip.federation.ldap.enabled=true}.</p>
 */
@Component
@ConditionalOnProperty(prefix = "tulip.federation.ldap", name = "enabled", havingValue = "true", matchIfMissing = false)
public class LdapFederationProvider extends AbstractStubFederationProvider {

    /** 어댑터 타입 상수. */
    public static final String TYPE = "LDAP";

    /** 기본 providerId (테넌트별 다수 등록 시 등록 데이터 기준으로 덮어쓴다). */
    public static final String DEFAULT_PROVIDER_ID = "ldap-default";

    @Override
    public String type() {
        return TYPE;
    }

    @Override
    public String providerId() {
        return DEFAULT_PROVIDER_ID;
    }
}
