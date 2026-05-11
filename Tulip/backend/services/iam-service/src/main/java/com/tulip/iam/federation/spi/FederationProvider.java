package com.tulip.iam.federation.spi;

import com.tulip.iam.federation.dto.FederationAuthorizeRequest;
import com.tulip.iam.federation.dto.FederationCallbackPayload;
import com.tulip.iam.federation.dto.FederationLoginContext;
import com.tulip.iam.federation.dto.FederationUserProfile;

/**
 * 외부 IdP 연동을 위한 Federation 어댑터 SPI.
 *
 * <p>SAML 2.0 / OIDC / LDAP 등 프로토콜별 구현체가 본 인터페이스를 구현한다.
 * Phase 1-B 에서는 모든 구현이 스텁 상태로 {@code TLP-AUT-FED-501} 을 던지며,
 * Phase 3 에서 실제 IdP 통신 로직을 채운다.</p>
 *
 * <p>참고: {@code 05_security_and_auth.md} §5.3 SSO·LDAP 연동.</p>
 *
 * <h3>구현 규약</h3>
 * <ul>
 *   <li>구현체는 Spring {@code @Component} 로 등록되며,
 *       {@code tulip.federation.{type}.enabled} 가 true 일 때만 활성화된다.</li>
 *   <li>모든 외부 호출은 timeout · circuit breaker 로 보호되어야 한다 (Phase 3).</li>
 *   <li>외부 식별자({@code externalId}) 는 내부 user_id 로 매핑되며, 매핑 테이블은
 *       {@code iam_federation_link} 에 저장한다.</li>
 * </ul>
 */
public interface FederationProvider {

    /**
     * 어댑터 프로토콜 타입.
     *
     * @return "SAML" / "OIDC" / "LDAP" 등 대문자 식별자
     */
    String type();

    /**
     * IdP 식별자.
     *
     * <p>테넌트별로 다수의 IdP 를 등록할 수 있으므로 본 식별자는
     * {@code iam_federation_provider.provider_id} 값과 일치해야 한다.
     * 스텁 구현은 자신의 타입을 그대로 반환할 수 있다.</p>
     *
     * @return IdP 식별자
     */
    String providerId();

    /**
     * 외부 IdP 로 사용자를 보낼 인가 요청을 생성한다.
     *
     * <p>OIDC 의 경우 authorization endpoint URL, SAML 의 경우 인코딩된
     * AuthnRequest 리다이렉트 URL 을 반환한다.</p>
     *
     * @param ctx 로그인 컨텍스트 (테넌트·providerId·returnUri·state)
     * @return 사용자에게 반환할 리다이렉트 정보
     */
    FederationAuthorizeRequest buildAuthorizeRequest(FederationLoginContext ctx);

    /**
     * IdP 콜백을 처리하여 사용자 프로필을 반환한다.
     *
     * <p>state/nonce/서명 검증 후, IdP 로부터 받은 속성을 {@link FederationUserProfile}
     * 로 변환해 반환한다. 호출 측은 결과를 받아 JIT 프로비저닝 또는 매핑된 사용자 조회를 수행한다.</p>
     *
     * @param payload 콜백 페이로드
     * @return 사용자 프로필
     */
    FederationUserProfile handleCallback(FederationCallbackPayload payload);

    /**
     * JIT(Just-In-Time) 프로비저닝 지원 여부.
     *
     * <p>true 인 경우 콜백 단계에서 미존재 사용자를 자동 생성한다.
     * 정책상 JIT 가 금지된 환경(예: 사전 등록만 허용)에서는 false 를 반환한다.</p>
     *
     * @return JIT 지원 여부
     */
    boolean supportsJit();
}
