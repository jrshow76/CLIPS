package com.tulip.iam.auth.web;

import com.tulip.common.core.exception.BusinessException;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.error.AuthErrorCode;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.iam.auth.dto.LoginDtos;
import com.tulip.iam.auth.service.AuthService;
import com.tulip.iam.config.IamProperties;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * Tulip+ IAM 인증 BFF 컨트롤러.
 *
 * <p>모든 응답은 {@link ApiResponse} envelope 으로 래핑된다 ({@code 03_api_standards.md} §4.1).
 * Refresh Token 은 항상 HttpOnly Secure Cookie 로만 노출되고, 본문(JSON) 에는 포함되지 않는다.</p>
 */
@RestController
@RequestMapping("/api/v1/auth")
@Tag(name = "auth", description = "OAuth2/PKCE 인증 BFF")
public class AuthController {

    private final AuthService authService;
    private final IamProperties props;

    public AuthController(AuthService authService, IamProperties props) {
        this.authService = authService;
        this.props = props;
    }

    @PostMapping("/login/initiate")
    @Operation(summary = "OAuth2 인가 코드 요청 URL 생성", description = "PKCE state/code_verifier 를 서버측에서 생성하여 Keycloak authorize URL 을 반환한다.")
    public ApiResponse<LoginDtos.InitiateResponse> initiate(@RequestBody(required = false) LoginDtos.InitiateRequest body) {
        return ApiResponse.success(authService.initiate(body == null ? new LoginDtos.InitiateRequest(null, null) : body));
    }

    @PostMapping("/login/callback")
    @Operation(summary = "Authorization Code 콜백 처리", description = "code + state 로 토큰을 교환하고 Refresh 는 HttpOnly Cookie 로 발급한다.")
    public ResponseEntity<ApiResponse<LoginDtos.TokenResponse>> callback(
            @Valid @RequestBody LoginDtos.CallbackRequest req,
            HttpServletRequest request,
            HttpServletResponse response) {

        AuthService.TokenExchangeResult result = authService.callback(
                req,
                request.getRemoteAddr(),
                request.getHeader(HttpHeaders.USER_AGENT));

        attachRefreshCookie(response, result.refreshToken());

        LoginDtos.TokenResponse body = new LoginDtos.TokenResponse(
                result.accessToken(),
                "Bearer",
                result.expiresIn(),
                null,
                result.scope()
        );
        return ResponseEntity.ok(ApiResponse.success(body));
    }

    @PostMapping("/refresh")
    @Operation(summary = "Refresh 토큰 회전", description = "구 Refresh 의 JTI 를 블랙리스트에 등록하고 새 Access/Refresh 를 발급한다.")
    public ResponseEntity<ApiResponse<LoginDtos.TokenResponse>> refresh(
            HttpServletRequest request,
            HttpServletResponse response) {

        String refreshToken = readRefreshCookie(request);
        AuthService.TokenExchangeResult result = authService.rotateRefresh(
                refreshToken,
                request.getRemoteAddr(),
                request.getHeader(HttpHeaders.USER_AGENT));

        attachRefreshCookie(response, result.refreshToken());

        LoginDtos.TokenResponse body = new LoginDtos.TokenResponse(
                result.accessToken(),
                "Bearer",
                result.expiresIn(),
                null,
                result.scope()
        );
        return ResponseEntity.ok(ApiResponse.success(body));
    }

    @PostMapping("/logout")
    @Operation(summary = "로그아웃", description = "Access/Refresh JTI 를 블랙리스트에 등록하고 Keycloak end-session 을 호출한다.")
    public ResponseEntity<ApiResponse<Void>> logout(
            HttpServletRequest request,
            HttpServletResponse response,
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization) {
        String accessToken = extractBearer(authorization);
        String refreshToken = readRefreshCookie(request);
        authService.logout(accessToken, refreshToken,
                request.getRemoteAddr(),
                request.getHeader(HttpHeaders.USER_AGENT));
        clearRefreshCookie(response);
        return ResponseEntity.ok(ApiResponse.success(null));
    }

    @GetMapping("/me")
    @Operation(summary = "현재 사용자 정보", description = "JWT 클레임에서 추출한 사용자 프로필을 반환한다.")
    public ApiResponse<LoginDtos.MeResponse> me() {
        TulipUserPrincipal p = currentPrincipal();
        LoginDtos.MeResponse body = new LoginDtos.MeResponse(
                p.userId(),
                p.tenantId(),
                p.memberType(),
                p.primaryLibraryId(),
                p.libraryIds(),
                p.roles() == null ? List.of() : p.roles().stream().toList(),
                p.scopes() == null ? List.of() : p.scopes().stream().toList()
        );
        return ApiResponse.success(body);
    }

    @GetMapping("/introspect")
    @Operation(summary = "토큰 인트로스펙션 (서비스 간 호출)", description = "주어진 Bearer 토큰의 유효성을 검사하고 클레임 요약을 반환한다.")
    public ApiResponse<LoginDtos.IntrospectResponse> introspect(
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization) {
        String token = extractBearer(authorization);
        if (token == null) {
            throw new BusinessException(AuthErrorCode.TOKEN_MISSING);
        }
        return ApiResponse.success(authService.introspect(token));
    }

    /* ============================== helpers ============================== */

    private TulipUserPrincipal currentPrincipal() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || auth.getPrincipal() == null
                || !(auth.getPrincipal() instanceof TulipUserPrincipal p)) {
            throw new BusinessException(AuthErrorCode.TOKEN_MISSING);
        }
        return p;
    }

    private String readRefreshCookie(HttpServletRequest request) {
        if (request.getCookies() == null) {
            return null;
        }
        for (Cookie c : request.getCookies()) {
            if (props.refreshCookie().name().equals(c.getName())) {
                return c.getValue();
            }
        }
        return null;
    }

    private void attachRefreshCookie(HttpServletResponse response, String refreshToken) {
        if (refreshToken == null) {
            return;
        }
        Cookie cookie = new Cookie(props.refreshCookie().name(), refreshToken);
        cookie.setHttpOnly(true);
        cookie.setSecure(props.refreshCookie().secure());
        cookie.setPath(props.refreshCookie().path());
        cookie.setMaxAge((int) props.refreshCookie().maxAge().toSeconds());
        cookie.setAttribute("SameSite", props.refreshCookie().sameSite());
        response.addCookie(cookie);
    }

    private void clearRefreshCookie(HttpServletResponse response) {
        Cookie cookie = new Cookie(props.refreshCookie().name(), "");
        cookie.setHttpOnly(true);
        cookie.setSecure(props.refreshCookie().secure());
        cookie.setPath(props.refreshCookie().path());
        cookie.setMaxAge(0);
        response.addCookie(cookie);
    }

    private static String extractBearer(String authorization) {
        if (authorization == null) {
            return null;
        }
        if (authorization.regionMatches(true, 0, "Bearer ", 0, 7)) {
            return authorization.substring(7).trim();
        }
        return null;
    }
}
