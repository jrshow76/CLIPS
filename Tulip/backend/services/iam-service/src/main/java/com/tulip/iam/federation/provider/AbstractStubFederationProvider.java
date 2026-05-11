package com.tulip.iam.federation.provider;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.iam.federation.dto.FederationAuthorizeRequest;
import com.tulip.iam.federation.dto.FederationCallbackPayload;
import com.tulip.iam.federation.dto.FederationLoginContext;
import com.tulip.iam.federation.dto.FederationUserProfile;
import com.tulip.iam.federation.error.IamErrorCode;
import com.tulip.iam.federation.spi.FederationProvider;

/**
 * Phase 1-B Federation 어댑터 공통 스텁 베이스.
 *
 * <p>SAML / OIDC / LDAP 어댑터는 Phase 3 까지 실제 구현이 없으므로,
 * 본 추상 클래스에서 공통적으로 {@code TLP-AUT-FED-501}
 * ({@link IamErrorCode#FEDERATION_NOT_IMPLEMENTED}) 을 던진다.</p>
 *
 * <p>Phase 3 에서는 서브클래스가 buildAuthorizeRequest · handleCallback 을
 * override 하여 실제 프로토콜 로직으로 대체한다.</p>
 */
public abstract class AbstractStubFederationProvider implements FederationProvider {

    /**
     * 스텁 표준 메시지 빌더. {@code type} 을 메시지에 삽입한다.
     */
    protected BusinessException notImplemented() {
        return new BusinessException(
                IamErrorCode.FEDERATION_NOT_IMPLEMENTED,
                "Federation provider not yet implemented: " + type()
        );
    }

    @Override
    public FederationAuthorizeRequest buildAuthorizeRequest(FederationLoginContext ctx) {
        throw notImplemented();
    }

    @Override
    public FederationUserProfile handleCallback(FederationCallbackPayload payload) {
        throw notImplemented();
    }

    /**
     * 스텁 단계에서는 JIT 가 정책상 활성화되지 않은 상태이므로 false 로 고정한다.
     * Phase 3 에서 운영 정책에 따라 서브클래스가 override 한다.
     */
    @Override
    public boolean supportsJit() {
        return false;
    }
}
