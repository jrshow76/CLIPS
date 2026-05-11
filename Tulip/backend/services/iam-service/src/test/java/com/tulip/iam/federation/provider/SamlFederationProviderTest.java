package com.tulip.iam.federation.provider;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.iam.federation.dto.FederationCallbackPayload;
import com.tulip.iam.federation.dto.FederationLoginContext;
import com.tulip.iam.federation.error.IamErrorCode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * {@link SamlFederationProvider} 스텁 단위 테스트.
 *
 * <p>Phase 1-B 시점에 모든 SAML 어댑터 호출이 {@code TLP-AUT-FED-501} 로 종료되는지 검증한다.</p>
 */
class SamlFederationProviderTest {

    private final SamlFederationProvider provider = new SamlFederationProvider();

    @Test
    @DisplayName("type() 은 SAML 을 반환한다")
    void typeIsSaml() {
        assertThat(provider.type()).isEqualTo("SAML");
    }

    @Test
    @DisplayName("buildAuthorizeRequest 호출 시 TLP-AUT-FED-501 을 던진다")
    void buildAuthorizeRequestThrowsNotImplemented() {
        FederationLoginContext ctx = new FederationLoginContext(
                "tnt_001", "saml-default", "https://opac.example.com/callback", "state-1"
        );

        assertThatThrownBy(() -> provider.buildAuthorizeRequest(ctx))
                .isInstanceOf(BusinessException.class)
                .satisfies(ex -> {
                    BusinessException be = (BusinessException) ex;
                    assertThat(be.errorCode().code()).isEqualTo("TLP-AUT-FED-501");
                    assertThat(be.errorCode()).isEqualTo(IamErrorCode.FEDERATION_NOT_IMPLEMENTED);
                    assertThat(be.getMessage()).contains("SAML");
                });
    }

    @Test
    @DisplayName("handleCallback 호출 시 TLP-AUT-FED-501 을 던진다")
    void handleCallbackThrowsNotImplemented() {
        FederationCallbackPayload payload = new FederationCallbackPayload(
                "saml-default", Map.of("SAMLResponse", "dummy")
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
