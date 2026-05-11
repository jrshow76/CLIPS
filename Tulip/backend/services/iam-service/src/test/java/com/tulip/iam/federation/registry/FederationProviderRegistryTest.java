package com.tulip.iam.federation.registry;

import com.tulip.iam.federation.provider.LdapFederationProvider;
import com.tulip.iam.federation.provider.OidcFederationProvider;
import com.tulip.iam.federation.provider.SamlFederationProvider;
import com.tulip.iam.federation.spi.FederationProvider;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link FederationProviderRegistry} 동작 검증.
 *
 * <p>SAML / OIDC / LDAP 어댑터 빈이 주입되었을 때 type · providerId 로의
 * 조회가 정상 동작하는지 확인한다.</p>
 */
class FederationProviderRegistryTest {

    private FederationProviderRegistry registryOf(FederationProvider... providers) {
        return new FederationProviderRegistry(List.of(providers));
    }

    @Test
    @DisplayName("어댑터 3종이 주입되면 size 는 3 이며 type 별로 조회 가능하다")
    void allThreeProvidersAreRegistered() {
        FederationProviderRegistry registry = registryOf(
                new SamlFederationProvider(),
                new OidcFederationProvider(),
                new LdapFederationProvider()
        );

        assertThat(registry.size()).isEqualTo(3);
        assertThat(registry.findByType("SAML")).hasSize(1);
        assertThat(registry.findByType("OIDC")).hasSize(1);
        assertThat(registry.findByType("LDAP")).hasSize(1);
        // 대소문자 무관 조회
        assertThat(registry.findByType("saml")).hasSize(1);
    }

    @Test
    @DisplayName("providerId 로 단건 조회가 동작한다")
    void findByProviderIdReturnsRegistered() {
        FederationProviderRegistry registry = registryOf(
                new SamlFederationProvider(),
                new OidcFederationProvider(),
                new LdapFederationProvider()
        );

        Optional<FederationProvider> saml = registry.findByProviderId(SamlFederationProvider.DEFAULT_PROVIDER_ID);
        assertThat(saml).isPresent();
        assertThat(saml.get().type()).isEqualTo("SAML");
    }

    @Test
    @DisplayName("미등록 providerId 는 Optional.empty 를 반환한다")
    void findByProviderIdReturnsEmptyWhenAbsent() {
        FederationProviderRegistry registry = registryOf(new SamlFederationProvider());

        assertThat(registry.findByProviderId("nonexistent")).isEmpty();
        assertThat(registry.findByProviderId(null)).isEmpty();
    }

    @Test
    @DisplayName("미등록 type 는 빈 리스트를 반환한다")
    void findByTypeReturnsEmptyWhenAbsent() {
        FederationProviderRegistry registry = registryOf(new SamlFederationProvider());

        assertThat(registry.findByType("OIDC")).isEmpty();
        assertThat(registry.findByType(null)).isEmpty();
    }

    @Test
    @DisplayName("어댑터가 한 개도 없어도 레지스트리는 정상 생성된다 (모두 disabled 인 환경)")
    void emptyRegistryIsAllowed() {
        FederationProviderRegistry registry = registryOf();

        assertThat(registry.size()).isZero();
        assertThat(registry.all()).isEmpty();
    }
}
