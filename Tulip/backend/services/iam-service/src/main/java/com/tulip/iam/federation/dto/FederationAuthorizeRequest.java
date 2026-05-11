package com.tulip.iam.federation.dto;

import java.util.Map;

/**
 * 외부 IdP 로 사용자를 리다이렉트하기 위한 인가 요청 결과 DTO.
 *
 * <p>SAML 2.0 의 경우 AuthnRequest 가 인코딩된 redirect URL, OIDC 의 경우
 * authorization endpoint URL 이 {@code redirectUrl} 에 담긴다.</p>
 *
 * @param redirectUrl       사용자를 보낼 IdP URL (필수)
 * @param state             CSRF 방지·세션 추적용 토큰 (callback 검증에 사용)
 * @param nonce             OIDC nonce 또는 SAML RequestID (재생 공격 방지)
 * @param additionalParams  추가 쿼리/폼 파라미터 (예: SAMLRequest, RelayState)
 */
public record FederationAuthorizeRequest(
        String redirectUrl,
        String state,
        String nonce,
        Map<String, String> additionalParams
) {

    /** 추가 파라미터 없이 생성하는 편의 생성자. */
    public FederationAuthorizeRequest(String redirectUrl, String state, String nonce) {
        this(redirectUrl, state, nonce, Map.of());
    }
}
