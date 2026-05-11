package com.tulip.iam.mfa;

import com.tulip.common.core.error.ErrorCode;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.core.response.ErrorDetail;
import com.tulip.common.core.trace.TraceContext;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * MFA 엔드포인트 스텁 (Sprint 1-B.8).
 *
 * <p>Phase 1-B 에서는 501 Not Implemented + 표준 코드 {@code TLP-AUT-MFA-501} 을 반환한다.
 * Phase 2 에서 본 컨트롤러를 TOTP/WebAuthn 구현으로 교체한다.</p>
 */
@RestController
@RequestMapping("/api/v1/auth/mfa")
@Tag(name = "auth-mfa", description = "MFA(TOTP/WebAuthn) — Phase 2 활성화 예정")
public class MfaController {

    /** Phase 1-B 임시 코드. 정식 등재 전 사용. */
    private static final ErrorCode MFA_NOT_IMPLEMENTED = new ErrorCode() {
        @Override public String code() { return "TLP-AUT-MFA-501"; }
        @Override public int httpStatus() { return 501; }
        @Override public String messageKey() { return "error.aut.mfa.not_implemented"; }
        @Override public String defaultMessage() { return "MFA 기능은 아직 구현되지 않았습니다"; }
        @Override public String defaultUserMessage() { return "추가 인증은 추후 활성화 예정입니다."; }
    };

    @PostMapping("/setup")
    @Operation(summary = "MFA 시크릿 등록 (스텁)")
    public ResponseEntity<ApiResponse<Void>> setup() {
        return notImplemented();
    }

    @PostMapping("/verify")
    @Operation(summary = "MFA 코드 검증 (스텁)")
    public ResponseEntity<ApiResponse<Void>> verify() {
        return notImplemented();
    }

    private ResponseEntity<ApiResponse<Void>> notImplemented() {
        ApiResponse<Void> body = ApiResponse.<Void>failure(
                        MFA_NOT_IMPLEMENTED.code(),
                        MFA_NOT_IMPLEMENTED.defaultMessage(),
                        ErrorDetail.of(MFA_NOT_IMPLEMENTED.messageKey(), MFA_NOT_IMPLEMENTED.defaultUserMessage()))
                .withTraceId(TraceContext.currentTraceId());
        return ResponseEntity.status(HttpStatus.NOT_IMPLEMENTED).body(body);
    }
}
