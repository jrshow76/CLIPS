package com.tulip.common.core.response;

import com.tulip.common.core.error.CommonErrorCode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@link ApiResponse} 단위 테스트.
 */
class ApiResponseTest {

    @Test
    @DisplayName("성공 응답은 success=true 이고 code=OK 이다")
    void successResponseShape() {
        ApiResponse<String> res = ApiResponse.success("hello");

        assertThat(res.success()).isTrue();
        assertThat(res.code()).isEqualTo("OK");
        assertThat(res.data()).isEqualTo("hello");
        assertThat(res.error()).isNull();
        assertThat(res.timestamp()).isNotNull();
    }

    @Test
    @DisplayName("실패 응답은 success=false 이고 code 는 TLP-* 형식이다")
    void failureResponseShape() {
        ErrorDetail detail = ErrorDetail.of(
                CommonErrorCode.VALIDATION_REQUIRED.messageKey(),
                "입력값을 다시 확인해 주세요");

        ApiResponse<Void> res = ApiResponse.failure(
                CommonErrorCode.VALIDATION_REQUIRED.code(),
                CommonErrorCode.VALIDATION_REQUIRED.defaultMessage(),
                detail);

        assertThat(res.success()).isFalse();
        assertThat(res.code()).startsWith("TLP-CMN-");
        assertThat(res.error()).isNotNull();
        assertThat(res.error().messageKey()).isEqualTo("error.cmn.validation.required");
    }

    @Test
    @DisplayName("withTraceId 는 동일 내용에 traceId 만 채운 새 응답을 반환한다")
    void withTraceIdCopies() {
        ApiResponse<String> base = ApiResponse.success("x");
        ApiResponse<String> traced = base.withTraceId("abc");

        assertThat(traced.traceId()).isEqualTo("abc");
        assertThat(traced.data()).isEqualTo("x");
        assertThat(base.traceId()).isNull();
    }
}
