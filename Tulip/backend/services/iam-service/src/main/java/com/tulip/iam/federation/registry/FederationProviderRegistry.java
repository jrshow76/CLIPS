package com.tulip.iam.federation.registry;

import com.tulip.iam.federation.spi.FederationProvider;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * Federation 어댑터 레지스트리.
 *
 * <p>Spring 컨테이너에서 활성화된 모든 {@link FederationProvider} 빈을 주입받아
 * {@code type} / {@code providerId} 기준으로 조회 가능한 맵을 구성한다.</p>
 *
 * <p>Phase 1-B 단계에서는 {@code tulip.federation.{saml|oidc|ldap}.enabled=true}
 * 인 어댑터만 등록되며, 운영기관의 활성화 정책을 그대로 반영한다.</p>
 */
@Component
public class FederationProviderRegistry {

    /** providerId → Provider. providerId 가 시스템 전역 유일이라는 전제이며,
     *  실제 라우팅 시 tenantId 와 함께 검증한다. */
    private final Map<String, FederationProvider> byProviderId;

    /** type(대문자) → Provider 목록. 동일 타입의 다수 등록 가능. */
    private final Map<String, List<FederationProvider>> byType;

    public FederationProviderRegistry(List<FederationProvider> providers) {
        this.byProviderId = providers.stream()
                .collect(Collectors.toUnmodifiableMap(
                        FederationProvider::providerId,
                        p -> p,
                        (a, b) -> a  // 동일 providerId 충돌 시 우선 등록 유지
                ));
        this.byType = providers.stream()
                .collect(Collectors.collectingAndThen(
                        Collectors.groupingBy(p -> p.type().toUpperCase(Locale.ROOT)),
                        Map::copyOf
                ));
    }

    /** providerId 로 어댑터를 조회한다. */
    public Optional<FederationProvider> findByProviderId(String providerId) {
        if (providerId == null) {
            return Optional.empty();
        }
        return Optional.ofNullable(byProviderId.get(providerId));
    }

    /** type(SAML/OIDC/LDAP) 으로 어댑터 목록을 조회한다. */
    public List<FederationProvider> findByType(String type) {
        if (type == null) {
            return List.of();
        }
        return byType.getOrDefault(type.toUpperCase(Locale.ROOT), List.of());
    }

    /** 등록된 어댑터 수. */
    public int size() {
        return byProviderId.size();
    }

    /** 등록된 모든 어댑터 (디버깅·헬스체크용). */
    public List<FederationProvider> all() {
        return List.copyOf(byProviderId.values());
    }
}
