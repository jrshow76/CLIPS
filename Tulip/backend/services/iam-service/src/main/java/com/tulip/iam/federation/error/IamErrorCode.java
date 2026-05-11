package com.tulip.iam.federation.error;

import com.tulip.common.core.error.ErrorCode;

/**
 * IAM 서비스 내부에서 사용하는 도메인 에러 코드 집합.
 *
 * <p>본 enum 은 {@code 04_error_codes.md} 의 표준 형식
 * {@code TLP-{DOMAIN}-{HTTP}-{SEQ}} 를 따른다. AUT 도메인의 5.1 표에 정의되지 않은
 * IAM 내부 신규 코드(예: 외부 SSO 어댑터 미구현)를 본 enum 으로 발급한다.</p>
 *
 * <p>도메인 표준 표(5.1)에 이미 등재된 코드(예: TLP-AUT-401-0007)는 그대로 사용하고,
 * 본 enum 에는 표에 없는 신규 코드만 등록한다. 표 등재 신청은 DevLead 승인 절차를 따른다.</p>
 *
 * <p>BackendDev 가이드(1-B.9): 신규 코드 {@code TLP-AUT-FED-501} 은 외부 SSO Federation
 * 어댑터가 스텁 상태이며 아직 구현되지 않았음을 알리는 501 Not Implemented 응답에 사용된다.
 * Phase 3 에서 실제 IdP 연동 시 본 코드는 더 이상 발생하지 않아야 한다.</p>
 */
public enum IamErrorCode implements ErrorCode {

    /**
     * 외부 SSO Federation 어댑터 미구현.
     *
     * <p>코드는 표준 형식의 변형으로, HTTP 자리에 {@code FED-501} 을 사용한다.
     * 이는 Federation 서브도메인을 시각적으로 구분하기 위한 IAM 서비스 내부 약속이며
     * DevLead 가이드에 따른다. HTTP 상태 코드는 501 Not Implemented 로 매핑된다.</p>
     */
    FEDERATION_NOT_IMPLEMENTED(
            "TLP-AUT-FED-501",
            501,
            "error.aut.federation.not_implemented",
            "외부 SSO 연동이 아직 구현되지 않았습니다",
            "외부 인증 연동은 추후 활성화 예정입니다. 관리자에게 문의해 주세요."
    ),

    /**
     * 요청한 Federation Provider 를 찾을 수 없음.
     *
     * <p>tenantId · providerId 조합으로 등록된 IdP 가 없을 때 발생.</p>
     */
    FEDERATION_PROVIDER_NOT_FOUND(
            "TLP-AUT-FED-404",
            404,
            "error.aut.federation.provider_not_found",
            "요청한 외부 SSO Provider 를 찾을 수 없습니다",
            "외부 인증 정보를 확인해 주세요."
    ),

    /**
     * Federation 콜백 페이로드 유효성 위반.
     *
     * <p>state · nonce · 서명 불일치 등 상태 검증 실패.</p>
     */
    FEDERATION_CALLBACK_INVALID(
            "TLP-AUT-FED-400",
            400,
            "error.aut.federation.callback_invalid",
            "외부 SSO 콜백 페이로드가 유효하지 않습니다",
            "외부 인증 처리 중 오류가 발생했습니다. 다시 시도해 주세요."
    );

    private final String code;
    private final int httpStatus;
    private final String messageKey;
    private final String defaultMessage;
    private final String defaultUserMessage;

    IamErrorCode(String code, int httpStatus, String messageKey,
                 String defaultMessage, String defaultUserMessage) {
        this.code = code;
        this.httpStatus = httpStatus;
        this.messageKey = messageKey;
        this.defaultMessage = defaultMessage;
        this.defaultUserMessage = defaultUserMessage;
    }

    @Override
    public String code() {
        return code;
    }

    @Override
    public int httpStatus() {
        return httpStatus;
    }

    @Override
    public String messageKey() {
        return messageKey;
    }

    @Override
    public String defaultMessage() {
        return defaultMessage;
    }

    @Override
    public String defaultUserMessage() {
        return defaultUserMessage;
    }
}
