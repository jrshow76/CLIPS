package com.footprint.common.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public enum ErrorCode {

    // 인증 (AUTH)
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED,    "AUTH_001", "이메일 또는 비밀번호가 올바르지 않습니다."),
    EMAIL_ALREADY_EXISTS(HttpStatus.CONFLICT,        "AUTH_002", "이미 사용 중인 이메일입니다."),
    INVALID_TOKEN(HttpStatus.UNAUTHORIZED,           "AUTH_003", "유효하지 않은 토큰입니다."),
    EXPIRED_TOKEN(HttpStatus.UNAUTHORIZED,           "AUTH_004", "만료된 토큰입니다."),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED,            "AUTH_005", "로그인이 필요합니다."),
    FORBIDDEN(HttpStatus.FORBIDDEN,                  "AUTH_006", "접근 권한이 없습니다."),

    // 장소 (PLACE)
    PLACE_NOT_FOUND(HttpStatus.NOT_FOUND,            "PLACE_001", "장소를 찾을 수 없습니다."),
    PLACE_PHOTO_LIMIT(HttpStatus.BAD_REQUEST,        "PLACE_002", "사진은 최대 5장까지 등록 가능합니다."),
    INVALID_COORDINATES(HttpStatus.BAD_REQUEST,      "PLACE_003", "유효하지 않은 좌표입니다."),
    FUTURE_DATE_NOT_ALLOWED(HttpStatus.BAD_REQUEST,  "PLACE_004", "방문일은 오늘 이전 날짜만 입력 가능합니다."),

    // 카테고리 (CATEGORY)
    CATEGORY_NOT_FOUND(HttpStatus.NOT_FOUND,         "CATEGORY_001", "카테고리를 찾을 수 없습니다."),
    CATEGORY_IN_USE(HttpStatus.CONFLICT,             "CATEGORY_002", "해당 카테고리를 사용 중인 장소가 있습니다."),
    DEFAULT_CATEGORY_IMMUTABLE(HttpStatus.BAD_REQUEST,"CATEGORY_003", "기본 카테고리는 수정하거나 삭제할 수 없습니다."),
    CATEGORY_LIMIT(HttpStatus.BAD_REQUEST,           "CATEGORY_004", "카테고리는 최대 20개까지 생성 가능합니다."),
    DUPLICATE_CATEGORY_NAME(HttpStatus.CONFLICT,     "CATEGORY_005", "이미 사용 중인 카테고리 이름입니다."),

    // 파일 (FILE)
    FILE_UPLOAD_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "FILE_001", "파일 업로드에 실패했습니다."),
    INVALID_FILE_TYPE(HttpStatus.BAD_REQUEST,            "FILE_002", "지원하지 않는 파일 형식입니다. (JPEG, PNG, WebP 허용)"),
    FILE_SIZE_EXCEEDED(HttpStatus.BAD_REQUEST,           "FILE_003", "파일 크기는 10MB를 초과할 수 없습니다."),

    // 공통 (COMMON)
    INVALID_REQUEST(HttpStatus.BAD_REQUEST,          "COMMON_001", "요청 데이터가 올바르지 않습니다."),
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "COMMON_002", "서버 오류가 발생했습니다.");

    private final HttpStatus httpStatus;
    private final String code;
    private final String message;

    ErrorCode(HttpStatus httpStatus, String code, String message) {
        this.httpStatus = httpStatus;
        this.code = code;
        this.message = message;
    }
}
