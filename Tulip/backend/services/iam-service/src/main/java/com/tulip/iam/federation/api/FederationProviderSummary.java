package com.tulip.iam.federation.api;

/**
 * 테넌트에서 활성화된 IdP 의 사용자 노출 요약 정보.
 *
 * <p>{@code GET /api/v1/auth/federation/providers} 응답 본문 항목으로 사용된다.</p>
 *
 * @param providerId  IdP 식별자
 * @param type        프로토콜 타입 (SAML / OIDC / LDAP)
 * @param displayName 사용자 노출용 표시명
 */
public record FederationProviderSummary(
        String providerId,
        String type,
        String displayName
) {
}
