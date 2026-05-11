package com.tulip.iam.federation.dto;

import java.util.Map;

/**
 * IdP 콜백 요청에서 추출한 페이로드.
 *
 * <p>OIDC 의 경우 {@code code}, {@code state} 등이 {@code params} 에,
 * SAML 의 경우 {@code SAMLResponse}, {@code RelayState} 가 {@code params} 또는
 * {@code rawBody} 에 담긴다.</p>
 *
 * @param providerId  콜백을 처리할 IdP 식별자
 * @param params      쿼리/폼 파라미터 (key-value)
 * @param rawBody     원본 요청 본문 (SAML POST binding 의 base64 등)
 */
public record FederationCallbackPayload(
        String providerId,
        Map<String, String> params,
        String rawBody
) {

    /** rawBody 없이 params 만으로 생성하는 편의 생성자. */
    public FederationCallbackPayload(String providerId, Map<String, String> params) {
        this(providerId, params, null);
    }
}
