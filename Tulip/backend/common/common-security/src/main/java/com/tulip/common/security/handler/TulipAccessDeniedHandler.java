package com.tulip.common.security.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.core.response.ErrorDetail;
import com.tulip.common.core.trace.TraceContext;
import com.tulip.common.security.error.AuthErrorCode;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;

import java.io.IOException;

/**
 * 인가 실패(403) 시 Tulip+ 표준 {@link ApiResponse} envelope 으로 응답한다.
 *
 * <p>기본 매핑: TLP-AUT-403-0001 (권한 없음).
 * 테넌트 불일치는 별도 매핑이 필요하나, 일반 케이스로 처리하며 IAM/Gateway 의
 * TenantHeaderEnricherFilter 가 TLP-AUT-403-0002 를 직접 반환한다.</p>
 */
public class TulipAccessDeniedHandler implements AccessDeniedHandler {

    private final ObjectMapper objectMapper;

    public TulipAccessDeniedHandler(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public void handle(HttpServletRequest request,
                       HttpServletResponse response,
                       AccessDeniedException accessDeniedException) throws IOException {

        AuthErrorCode code = AuthErrorCode.PERMISSION_DENIED;
        ApiResponse<Void> body = ApiResponse.<Void>failure(
                        code.code(),
                        code.defaultMessage(),
                        ErrorDetail.of(code.messageKey(), code.defaultUserMessage()))
                .withTraceId(TraceContext.currentTraceId());

        response.setStatus(code.httpStatus());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        objectMapper.writeValue(response.getOutputStream(), body);
    }
}
