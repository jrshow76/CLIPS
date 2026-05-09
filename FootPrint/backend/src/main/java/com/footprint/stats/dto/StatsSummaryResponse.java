package com.footprint.stats.dto;

public record StatsSummaryResponse(
        long totalPlaces,
        long thisMonthPlaces,
        Double avgRating,
        TopCategoryDto topCategory
) {
    public record TopCategoryDto(
            Long categoryId,
            String name,
            long placeCount
    ) {}
}
