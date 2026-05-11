package com.tulip.iam.federation.persistence;

import com.tulip.iam.federation.registry.FederationProviderConfig;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * 메모리 기반 Federation Provider 등록소 (Phase 1-B 스텁).
 *
 * <p>Phase 3 에서 DB 백엔드 구현으로 교체된다.
 * 테스트와 초기 통합을 위한 단순 저장소이며, 멀티노드 환경에서는 일관성을 보장하지 않는다.</p>
 */
@Repository
public class InMemoryFederationProviderRepository implements FederationProviderRepository {

    /** providerId → 등록 정보. */
    private final ConcurrentMap<String, FederationProviderConfig> store = new ConcurrentHashMap<>();

    /** 테스트·운영 콘솔에서 IdP 를 등록하기 위한 진입점. */
    public void register(FederationProviderConfig config) {
        store.put(config.providerId(), config);
    }

    /** 등록 데이터를 전부 비운다 (테스트 격리용). */
    public void clear() {
        store.clear();
    }

    @Override
    public List<FederationProviderConfig> findActiveByTenant(String tenantId) {
        if (tenantId == null) {
            return List.of();
        }
        List<FederationProviderConfig> result = new ArrayList<>();
        for (FederationProviderConfig cfg : store.values()) {
            if (tenantId.equals(cfg.tenantId()) && cfg.enabled()) {
                result.add(cfg);
            }
        }
        return List.copyOf(result);
    }

    @Override
    public Optional<FederationProviderConfig> findByProviderId(String providerId) {
        if (providerId == null) {
            return Optional.empty();
        }
        return Optional.ofNullable(store.get(providerId));
    }
}
