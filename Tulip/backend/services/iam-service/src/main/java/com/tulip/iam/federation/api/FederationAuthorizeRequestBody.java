package com.tulip.iam.federation.api;

import jakarta.validation.constraints.NotBlank;

/**
 * {@code POST /api/v1/auth/federation/authorize} 요청 본문.
 *
 * <p>클라이언트가 외부 IdP 로 리다이렉트 시작을 요청할 때 전달한다.</p>
 *
 * @param tenantId   테넌트 식별자 (필수)
 * @param providerId IdP 식별자 (필수)
 * @param returnUri  인증 완료 후 클라이언트 복귀 URL (필수)
 * @param state      클라이언트가 생성한 state 토큰 (옵션, 미전달 시 서버 발급)
 */
public record FederationAuthorizeRequestBody(
        @NotBlank String tenantId,
        @NotBlank String providerId,
        @NotBlank String returnUri,
        String state
) {
}
