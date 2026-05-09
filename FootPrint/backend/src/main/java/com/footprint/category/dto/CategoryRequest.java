package com.footprint.category.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record CategoryRequest(

        @NotBlank(message = "카테고리 이름은 필수입니다.")
        @Size(min = 1, max = 20, message = "카테고리 이름은 1~20자 이내여야 합니다.")
        String name,

        @Pattern(regexp = "^#[0-9A-Fa-f]{6}$", message = "색상은 #RRGGBB 형식이어야 합니다.")
        String color,

        @Size(max = 50, message = "아이콘 코드는 최대 50자 이내여야 합니다.")
        String icon
) {
}
