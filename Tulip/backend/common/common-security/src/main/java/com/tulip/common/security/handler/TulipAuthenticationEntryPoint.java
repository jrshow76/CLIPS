package com.tulip.common.security.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.core.response.ErrorDetail;
import com.tulip.common.core.trace.TraceContext;
import com.tulip.common.security.error.AuthErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;

import java.io.IOException;

/**
 * 인증 실패(401) 시 Tulip+ 표준 {@link ApiResponse} envelope 으로 응답한다.
 *
 * <p>매핑 규칙({@code 04_error_codes.md} §5.1):</p>
 * <ul>
 *   <li>토큰 누락 → TLP-AUT-401-0001</li>
 *   <li>만료 / 서명 실패 / 기타 → TLP-AUT-401-0003</li>
 * </ul>
 */
public class TulipAuthenticationEntryPoint implements AuthenticationEntryPoint {

    private final ObjectMapper objectMapper;

    public TulipAuthenticationEntryPoint(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public void commence(HttpServletRequest request,
                         HttpServletResponse response,
                         AuthenticationException authException) throws IOException {

        AuthErrorCode code = pickCode(request, authException);
        ApiResponse<Void> body = ApiResponse.<Void>failure(
                        code.code(),
                        code.defaultMessage(),
                        ErrorDetail.of(code.messageKey(), code.defaultUserMessage()))
                .withTraceId(TraceContext.currentTraceId());

        response.setStatus(code.httpStatus());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        response.setHeader("WWW-Authenticate", "Bearer realm=\"tulip\"");
        objectMapper.writeValue(response.getOutputStream(), body);
    }

    private AuthErrorCode pickCode(HttpServletRequest request, AuthenticationException ex) {
        String auth = request.getHeader("Authorization");
        if (auth == null || auth.isBlank()) {
            return AuthErrorCode.TOKEN_MISSING;
        }
        String msg = ex == null ? "" : String.valueOf(ex.getMessage()).toLowerCase();
        if (msg.contains("expired")) {
            return AuthErrorCode.TOKEN_EXPIRED;
        }
        return AuthErrorCode.TOKEN_INVALID;
    }
}
