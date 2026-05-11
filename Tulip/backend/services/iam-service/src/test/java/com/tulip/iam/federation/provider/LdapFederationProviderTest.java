package com.tulip.iam.federation.provider;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.iam.federation.dto.FederationCallbackPayload;
import com.tulip.iam.federation.dto.FederationLoginContext;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link LdapFederationProvider} 스텁 단위 테스트.
 */
class LdapFederationProviderTest {

    private final LdapFederationProvider provider = new LdapFederationProvider();

    @Test
    @DisplayName("type() 은 LDAP 을 반환한다")
    void typeIsLdap() {
        assertThat(provider.type()).isEqualTo("LDAP");
    }

    @Test
    @DisplayName("buildAuthorizeRequest 호출 시 TLP-AUT-FED-501 을 던진다")
    void buildAuthorizeRequestThrowsNotImplemented() {
        FederationLoginContext ctx = new FederationLoginContext(
                "tnt_001", "ldap-default", "https://admin.example.com/callback", "state-1"
        );

        assertThatThrownBy(() -> provider.buildAuthorizeRequest(ctx))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> {
                    BusinessException be = (BusinessException) ex;
                    assertThat(be.errorCode().code()).isEqualTo("TLP-AUT-FED-501");
                    assertThat(be.getMessage()).contains("LDAP");
                });
    }

    @Test
    @DisplayName("handleCallback 호출 시 TLP-AUT-FED-501 을 던진다")
    void handleCallbackThrowsNotImplemented() {
        FederationCallbackPayload payload = new FederationCallbackPayload(
                "ldap-default", Map.of("uid", "user1")
        );

        assertThatThrownBy(() -> provider.handleCallback(payload))
                .isInstanceOf(BusinessException.class)
                .extracting(ex -> ((BusinessException) ex).errorCode().code())
                .isEqualTo("TLP-AUT-FED-501");
    }

    @Test
    @DisplayName("supportsJit() 은 스텁 단계에서 false 를 반환한다")
    void supportsJitIsFalse() {
        assertThat(provider.supportsJit()).isFalse();
    }
}
