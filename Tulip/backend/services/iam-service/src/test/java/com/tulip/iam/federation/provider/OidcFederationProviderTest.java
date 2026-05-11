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
 * {@link OidcFederationProvider} 스텁 단위 테스트.
 */
class OidcFederationProviderTest {

    private final OidcFederationProvider provider = new OidcFederationProvider();

    @Test
    @DisplayName("type() 은 OIDC 를 반환한다")
    void typeIsOidc() {
        assertThat(provider.type()).isEqualTo("OIDC");
    }

    @Test
    @DisplayName("buildAuthorizeRequest 호출 시 TLP-AUT-FED-501 을 던진다")
    void buildAuthorizeRequestThrowsNotImplemented() {
        FederationLoginContext ctx = new FederationLoginContext(
                "tnt_001", "oidc-default", "https://admin.example.com/callback", "state-1"
        );

        assertThatThrownBy(() -> provider.buildAuthorizeRequest(ctx))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> {
                    BusinessException be = (BusinessException) ex;
                    assertThat(be.errorCode().code()).isEqualTo("TLP-AUT-FED-501");
                    assertThat(be.getMessage()).contains("OIDC");
                });
    }

    @Test
    @DisplayName("handleCallback 호출 시 TLP-AUT-FED-501 을 던진다")
    void handleCallbackThrowsNotImplemented() {
        FederationCallbackPayload payload = new FederationCallbackPayload(
                "oidc-default", Map.of("code", "abc", "state", "state-1")
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
