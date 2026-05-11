package com.tulip.iam.auth.dto;

import jakarta.validation.constraints.NotBlank;

import java.util.List;

/**
 * 인증 BFF 엔드포인트의 요청/응답 DTO 모음.
 *
 * <p>각 DTO 는 API 표준({@code 03_api_standards.md} §4.4) — camelCase, null 사용 — 을 준수한다.</p>
 */
public final class LoginDtos {

    private LoginDtos() {
    }

    /** /auth/login/initiate 요청. */
    public record InitiateRequest(
            String returnUri,
            String tenantHint
    ) {
    }

    /** /auth/login/initiate 응답. */
    public record InitiateResponse(
            String authorizeUrl,
            String state,
            String codeChallenge,
            String codeChallengeMethod
    ) {
    }

    /** /auth/login/callback 요청. */
    public record CallbackRequest(
            @NotBlank String code,
            @NotBlank String state
    ) {
    }

    /** /auth/login/callback 응답 — Access Token 본문 노출, Refresh 는 Set-Cookie. */
    public record TokenResponse(
            String accessToken,
            String tokenType,
            long expiresIn,
            String refreshTokenJti,
            String scope
    ) {
    }

    /** /auth/me 응답. */
    public record MeResponse(
            String userId,
            String tenantId,
            String memberType,
            String primaryBranchId,
            List<String> branchIds,
            List<String> roles,
            List<String> scopes
    ) {
    }

    /** /auth/introspect 응답. */
    public record IntrospectResponse(
            boolean active,
            String sub,
            String tenantId,
            List<String> branchIds,
            List<String> roles,
            String jti,
            Long exp
    ) {
    }
}
