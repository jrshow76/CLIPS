package com.shelfy.common.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum ErrorCode {

    // ===== 공통 =====
    INVALID_INPUT(HttpStatus.BAD_REQUEST, "COMMON-E001", "입력값이 올바르지 않습니다."),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "COMMON-E002", "인증이 필요합니다."),
    FORBIDDEN(HttpStatus.FORBIDDEN, "COMMON-E003", "접근 권한이 없습니다."),
    RESOURCE_NOT_FOUND(HttpStatus.NOT_FOUND, "COMMON-E004", "리소스를 찾을 수 없습니다."),
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "COMMON-I001", "서버 내부 오류가 발생했습니다."),

    // ===== 인증 (AUTH) =====
    EMAIL_DUPLICATED(HttpStatus.CONFLICT, "AUTH-E001", "이미 사용 중인 이메일입니다."),
    NICKNAME_DUPLICATED(HttpStatus.CONFLICT, "AUTH-E002", "이미 사용 중인 닉네임입니다."),
    PASSWORD_MISMATCH(HttpStatus.BAD_REQUEST, "AUTH-E003", "비밀번호가 일치하지 않습니다."),
    INVALID_EMAIL_FORMAT(HttpStatus.BAD_REQUEST, "AUTH-E004", "올바른 이메일 형식을 입력하세요."),
    PASSWORD_POLICY_VIOLATION(HttpStatus.BAD_REQUEST, "AUTH-E005",
            "비밀번호는 8~20자, 영문·숫자·특수문자를 포함해야 합니다."),
    REQUIRED_AGREEMENT_MISSING(HttpStatus.BAD_REQUEST, "AUTH-E006", "필수 약관에 동의해야 합니다."),
    EMAIL_VERIFICATION_TOKEN_EXPIRED(HttpStatus.BAD_REQUEST, "AUTH-E010",
            "인증 링크가 만료되었습니다. 재발송을 요청하세요."),
    EMAIL_VERIFICATION_TOKEN_INVALID(HttpStatus.BAD_REQUEST, "AUTH-E011",
            "유효하지 않은 인증 링크입니다."),
    EMAIL_ALREADY_VERIFIED(HttpStatus.CONFLICT, "AUTH-E012",
            "이미 이메일 인증이 완료된 계정입니다."),
    LOGIN_FAILED(HttpStatus.UNAUTHORIZED, "AUTH-E020", "이메일 또는 비밀번호를 확인하세요."),
    ACCOUNT_LOCKED(HttpStatus.FORBIDDEN, "AUTH-E021",
            "로그인 5회 실패로 계정이 잠금되었습니다. 30분 후 재시도하거나 비밀번호를 재설정하세요."),
    ACCOUNT_WITHDRAWN(HttpStatus.FORBIDDEN, "AUTH-E022", "탈퇴된 계정입니다."),
    REFRESH_TOKEN_EXPIRED(HttpStatus.UNAUTHORIZED, "AUTH-E030",
            "세션이 만료되었습니다. 다시 로그인하세요."),
    REFRESH_TOKEN_INVALID(HttpStatus.UNAUTHORIZED, "AUTH-E031",
            "인증 정보가 유효하지 않습니다. 다시 로그인하세요."),

    // ===== 상품 (ITEM) =====
    EMAIL_NOT_VERIFIED(HttpStatus.FORBIDDEN, "ITEM-E001",
            "이메일 인증 후 상품을 등록할 수 있습니다."),
    UNSUPPORTED_FILE_TYPE(HttpStatus.BAD_REQUEST, "ITEM-E002",
            "JPG, PNG, WEBP 형식의 이미지만 업로드 가능합니다."),
    FILE_SIZE_EXCEEDED(HttpStatus.BAD_REQUEST, "ITEM-E003",
            "이미지 1장당 최대 10MB까지 업로드 가능합니다."),
    IMAGE_COUNT_EXCEEDED(HttpStatus.BAD_REQUEST, "ITEM-E004",
            "이미지는 최대 10장까지 등록 가능합니다."),
    PRICE_OUT_OF_RANGE(HttpStatus.BAD_REQUEST, "ITEM-E005",
            "가격은 100원 이상 10,000,000원 이하여야 합니다."),
    INVALID_CATEGORY(HttpStatus.BAD_REQUEST, "ITEM-E006", "유효하지 않은 카테고리입니다."),
    SUBSCRIPTION_PLAN_REQUIRED(HttpStatus.BAD_REQUEST, "ITEM-E007",
            "구독 상품은 최소 1개의 플랜을 설정해야 합니다."),
    ITEM_UPDATE_FORBIDDEN(HttpStatus.FORBIDDEN, "ITEM-E020",
            "해당 상품을 수정할 권한이 없습니다."),
    PLAN_PRICE_UPDATE_FORBIDDEN(HttpStatus.UNPROCESSABLE_ENTITY, "ITEM-E021",
            "구독자가 있는 플랜의 가격은 변경할 수 없습니다."),
    ITEM_NOT_FOUND(HttpStatus.NOT_FOUND, "ITEM-E022", "상품을 찾을 수 없습니다."),
    ACTIVE_SUBSCRIBER_EXISTS(HttpStatus.UNPROCESSABLE_ENTITY, "ITEM-E030",
            "활성 구독자가 있는 상품은 삭제할 수 없습니다. 구독 종료 후 삭제하세요."),
    ITEM_DELETE_FORBIDDEN(HttpStatus.FORBIDDEN, "ITEM-E031",
            "해당 상품을 삭제할 권한이 없습니다."),

    // ===== 탐색 (BROWSE) =====
    BROWSE_ITEM_NOT_FOUND(HttpStatus.NOT_FOUND, "BROWSE-E001", "상품을 찾을 수 없습니다."),
    ITEM_PRIVATE(HttpStatus.FORBIDDEN, "BROWSE-E002", "비공개 상품입니다."),

    // ===== 주문 (ORDER) =====
    SELF_PURCHASE(HttpStatus.UNPROCESSABLE_ENTITY, "ORDER-E001",
            "본인 상품은 구매할 수 없습니다."),
    ORDER_ITEM_UNAVAILABLE(HttpStatus.NOT_FOUND, "ORDER-E002", "구매할 수 없는 상품입니다."),
    PAYMENT_FAILED(HttpStatus.PAYMENT_REQUIRED, "ORDER-E003",
            "결제에 실패했습니다. 잠시 후 다시 시도하세요."),
    SUBSCRIBE_ONLY_ITEM(HttpStatus.UNPROCESSABLE_ENTITY, "ORDER-E004",
            "해당 상품은 구독으로만 이용 가능합니다."),
    REFUND_PERIOD_EXPIRED(HttpStatus.UNPROCESSABLE_ENTITY, "ORDER-E010",
            "구매 후 7일이 경과하여 환불이 불가합니다."),
    CONTENT_ACCESSED(HttpStatus.UNPROCESSABLE_ENTITY, "ORDER-E011",
            "콘텐츠 열람 이력이 있어 환불이 불가합니다."),

    // ===== 구독 (SUB) =====
    ALREADY_SUBSCRIBED(HttpStatus.CONFLICT, "SUB-E001", "이미 해당 상품을 구독 중입니다."),
    SELF_SUBSCRIPTION(HttpStatus.UNPROCESSABLE_ENTITY, "SUB-E002",
            "본인 상품은 구독할 수 없습니다."),
    SUBSCRIPTION_NOT_SUPPORTED(HttpStatus.UNPROCESSABLE_ENTITY, "SUB-E003",
            "해당 상품은 구독을 지원하지 않습니다."),
    SUBSCRIPTION_PAYMENT_FAILED(HttpStatus.PAYMENT_REQUIRED, "SUB-E004",
            "결제에 실패했습니다. 결제 수단을 확인하세요.");

    private final HttpStatus httpStatus;
    private final String code;
    private final String message;
}
