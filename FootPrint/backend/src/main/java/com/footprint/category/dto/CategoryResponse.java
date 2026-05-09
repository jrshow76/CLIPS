package com.footprint.category.dto;

import com.footprint.category.entity.Category;

public record CategoryResponse(
        Long id,
        String name,
        String color,
        String icon,
        boolean isDefault,
        long placeCount
) {
    public static CategoryResponse from(Category category) {
        return new CategoryResponse(
                category.getId(),
                category.getName(),
                category.getColor(),
                category.getIcon(),
                category.isDefault(),
                0L
        );
    }

    public static CategoryResponse from(Category category, long placeCount) {
        return new CategoryResponse(
                category.getId(),
                category.getName(),
                category.getColor(),
                category.getIcon(),
                category.isDefault(),
                placeCount
        );
    }
}
