package com.footprint.auth.dto;

public record TokenResponse(
        String accessToken,
        String refreshToken,
        long accessTokenExpiresIn
) {}
