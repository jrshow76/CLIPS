package com.tulip.iam.federation.dto;

import java.util.Map;

/**
 * Federation 로그인 흐름의 입력 컨텍스트.
 *
 * <p>{@link com.tulip.iam.federation.spi.FederationProvider#buildAuthorizeRequest}
 * 호출 시 인증 요청 생성을 위해 필요한 입력값을 캡슐화한다.</p>
 *
 * @param tenantId    테넌트 식별자 (필수, 멀티테넌시 격리 의무)
 * @param providerId  IdP 식별자 (필수, 테넌트별 다수 등록 가능)
 * @param returnUri   인증 완료 후 사용자가 돌아갈 클라이언트 URL (allowed redirect 화이트리스트 검증 필요)
 * @param state       CSRF 방지용 state 토큰 (서버 발급, Phase 3 에서 검증)
 * @param extra       프로토콜별 부가 파라미터 (예: SAML RelayState, OIDC scope/acr_values)
 */
public record FederationLoginContext(
        String tenantId,
        String providerId,
        String returnUri,
        String state,
        Map<String, String> extra
) {

    /** extra 파라미터 없이 생성하는 편의 생성자. */
    public FederationLoginContext(String tenantId, String providerId, String returnUri, String state) {
        this(tenantId, providerId, returnUri, state, Map.of());
    }
}
