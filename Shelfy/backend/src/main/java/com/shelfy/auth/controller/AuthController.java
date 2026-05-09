package com.shelfy.auth.controller;

import com.shelfy.auth.dto.request.LoginRequest;
import com.shelfy.auth.dto.request.SignupRequest;
import com.shelfy.auth.dto.response.LoginResponse;
import com.shelfy.auth.dto.response.SignupResponse;
import com.shelfy.auth.service.AuthService;
import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.common.response.ApiResponse;
import com.shelfy.security.CustomUserDetails;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

import java.util.Arrays;
import java.util.Map;

/**
 * 인증 API 컨트롤러
 * <p>
 * Base URL: /api/v1/auth
 */
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private static final String REFRESH_TOKEN_COOKIE_NAME = "refreshToken";
    private static final String REFRESH_TOKEN_COOKIE_PATH = "/api/v1/auth/token";

    private final AuthService authService;

    @Value("${jwt.access-token-expiration}")
    private long accessTokenExpirationSeconds;

    @Value("${jwt.refresh-token-expiration}")
    private long refreshTokenExpirationSeconds;

    /**
     * POST /api/v1/auth/signup - 회원가입
     */
    @PostMapping("/signup")
    public ResponseEntity<ApiResponse<SignupResponse>> signup(
            @RequestBody @Valid SignupRequest request) {
        SignupResponse response = authService.signup(request);
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success(response));
    }

    /**
     * POST /api/v1/auth/login - 로그인
     * <p>
     * Access Token은 응답 바디, Refresh Token은 HttpOnly 쿠키로 전달한다.
     */
    @PostMapping("/login")
    public ResponseEntity<ApiResponse<LoginResponse>> login(
            @RequestBody @Valid LoginRequest request,
            HttpServletResponse response) {
        String[] tokens = authService.login(request);
        String accessToken = tokens[0];
        String rawRefreshToken = tokens[1];

        setRefreshTokenCookie(response, rawRefreshToken, (int) refreshTokenExpirationSeconds);

        LoginResponse loginResponse = LoginResponse.of(accessToken, accessTokenExpirationSeconds);
        return ResponseEntity.ok(ApiResponse.success(loginResponse));
    }

    /**
     * POST /api/v1/auth/logout - 로그아웃
     * <p>
     * Refresh Token을 무효화하고 쿠키를 만료시킨다.
     */
    @PostMapping("/logout")
    public ResponseEntity<Void> logout(
            @AuthenticationPrincipal CustomUserDetails userDetails,
            HttpServletRequest request,
            HttpServletResponse response) {
        String rawRefreshToken = extractRefreshTokenFromCookie(request);

        if (StringUtils.hasText(rawRefreshToken)) {
            authService.logoutWithToken(userDetails.getUserId(), rawRefreshToken);
        } else {
            authService.logout(userDetails.getUserId());
        }

        // 쿠키 만료 처리
        expireRefreshTokenCookie(response);

        return ResponseEntity.noContent().build();
    }

    /**
     * POST /api/v1/auth/token/refresh - Access Token 갱신
     * <p>
     * HttpOnly 쿠키의 Refresh Token을 사용한다.
     */
    @PostMapping("/token/refresh")
    public ResponseEntity<ApiResponse<LoginResponse>> refresh(
            HttpServletRequest request) {
        String rawRefreshToken = extractRefreshTokenFromCookie(request);

        if (!StringUtils.hasText(rawRefreshToken)) {
            throw new ShelfyException(ErrorCode.REFRESH_TOKEN_INVALID);
        }

        String newAccessToken = authService.refreshAccessToken(rawRefreshToken);
        LoginResponse loginResponse = LoginResponse.of(newAccessToken, accessTokenExpirationSeconds);
        return ResponseEntity.ok(ApiResponse.success(loginResponse));
    }

    /**
     * GET /api/v1/auth/verify-email - 이메일 인증
     */
    @GetMapping("/verify-email")
    public ResponseEntity<ApiResponse<Map<String, String>>> verifyEmail(
            @RequestParam String token) {
        authService.verifyEmail(token);
        return ResponseEntity.ok(ApiResponse.success(
                Map.of("message", "이메일 인증이 완료되었습니다.")));
    }

    /**
     * POST /api/v1/auth/resend-verification - 인증 이메일 재발송
     */
    @PostMapping("/resend-verification")
    public ResponseEntity<ApiResponse<Map<String, String>>> resendVerification(
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        authService.resendVerificationEmail(userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(
                Map.of("message", "인증 이메일을 재발송했습니다.")));
    }

    // ===== 내부 헬퍼 메서드 =====

    /**
     * HttpOnly Refresh Token 쿠키 설정
     */
    private void setRefreshTokenCookie(HttpServletResponse response,
            String refreshToken, int maxAgeSeconds) {
        Cookie cookie = new Cookie(REFRESH_TOKEN_COOKIE_NAME, refreshToken);
        cookie.setHttpOnly(true);
        cookie.setSecure(true);          // HTTPS only (운영 환경)
        cookie.setPath(REFRESH_TOKEN_COOKIE_PATH);
        cookie.setMaxAge(maxAgeSeconds);
        // SameSite=Strict - Cookie API가 직접 지원하지 않으므로 헤더로 추가
        response.addCookie(cookie);
        response.addHeader("Set-Cookie",
                REFRESH_TOKEN_COOKIE_NAME + "=" + refreshToken
                + "; HttpOnly; Secure; SameSite=Strict; Max-Age=" + maxAgeSeconds
                + "; Path=" + REFRESH_TOKEN_COOKIE_PATH);
    }

    /**
     * Refresh Token 쿠키 만료 처리
     */
    private void expireRefreshTokenCookie(HttpServletResponse response) {
        Cookie cookie = new Cookie(REFRESH_TOKEN_COOKIE_NAME, "");
        cookie.setHttpOnly(true);
        cookie.setSecure(true);
        cookie.setPath(REFRESH_TOKEN_COOKIE_PATH);
        cookie.setMaxAge(0);
        response.addCookie(cookie);
    }

    /**
     * 쿠키에서 Refresh Token 추출
     */
    private String extractRefreshTokenFromCookie(HttpServletRequest request) {
        if (request.getCookies() == null) {
            return null;
        }
        return Arrays.stream(request.getCookies())
                .filter(c -> REFRESH_TOKEN_COOKIE_NAME.equals(c.getName()))
                .findFirst()
                .map(Cookie::getValue)
                .orElse(null);
    }
}
