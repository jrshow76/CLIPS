package com.footprint.place.dto;

import jakarta.validation.constraints.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public record PlaceRequest(

        @NotBlank(message = "장소명은 필수입니다.")
        @Size(min = 1, max = 100, message = "장소명은 1~100자 이내여야 합니다.")
        String name,

        @Size(max = 255, message = "주소는 최대 255자 이내여야 합니다.")
        String address,

        @NotNull(message = "위도는 필수입니다.")
        @DecimalMin(value = "-90.0", message = "위도는 -90 이상이어야 합니다.")
        @DecimalMax(value = "90.0", message = "위도는 90 이하여야 합니다.")
        BigDecimal latitude,

        @NotNull(message = "경도는 필수입니다.")
        @DecimalMin(value = "-180.0", message = "경도는 -180 이상이어야 합니다.")
        @DecimalMax(value = "180.0", message = "경도는 180 이하여야 합니다.")
        BigDecimal longitude,

        @NotNull(message = "방문일은 필수입니다.")
        @PastOrPresent(message = "방문일은 오늘 이전 날짜만 입력 가능합니다.")
        LocalDate visitedAt,

        @Size(max = 2000, message = "메모는 최대 2000자 이내여야 합니다.")
        String memo,

        @Min(value = 1, message = "평점은 최소 1점입니다.")
        @Max(value = 5, message = "평점은 최대 5점입니다.")
        Short rating,

        @NotEmpty(message = "카테고리는 최소 1개 이상 선택해야 합니다.")
        List<Long> categoryIds,

        List<@Size(max = 20, message = "태그는 최대 20자 이내여야 합니다.") String> tags
) {
}
