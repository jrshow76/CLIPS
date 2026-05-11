package com.tulip.iam.federation.persistence;

import com.tulip.iam.federation.registry.FederationProviderConfig;

import java.util.List;
import java.util.Optional;

/**
 * 테넌트별 IdP 등록 정보를 조회·관리하는 리포지토리.
 *
 * <p>Phase 1-B 에서는 {@link InMemoryFederationProviderRepository} 기본 구현이 주입되며,
 * Phase 3 에서 {@code iam_federation_provider} 테이블 기반 MyBatis/JPA 구현으로
 * 대체된다.</p>
 */
public interface FederationProviderRepository {

    /** 테넌트의 활성화된 IdP 목록을 반환한다. */
    List<FederationProviderConfig> findActiveByTenant(String tenantId);

    /** providerId 로 단건 조회한다. */
    Optional<FederationProviderConfig> findByProviderId(String providerId);
}
