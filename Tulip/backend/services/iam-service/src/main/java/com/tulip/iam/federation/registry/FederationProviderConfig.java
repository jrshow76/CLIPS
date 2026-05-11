package com.tulip.iam.federation.registry;

/**
 * 테넌트별 Federation IdP 등록 설정 DTO.
 *
 * <p>{@code iam_federation_provider} 테이블 1행을 표현한다.
 * 운영자가 콘솔에서 등록한 IdP 정보를 메모리에 캐싱해 라우팅에 사용한다.</p>
 *
 * @param tenantId    테넌트 식별자
 * @param providerId  IdP 식별자 (테넌트 내 UNIQUE)
 * @param type        프로토콜 타입 ("SAML" / "OIDC" / "LDAP")
 * @param displayName 사용자 노출용 표시명 (예: "○○대학교 통합인증")
 * @param enabled     활성화 여부
 */
public record FederationProviderConfig(
        String tenantId,
        String providerId,
        String type,
        String displayName,
        boolean enabled
) {
}
