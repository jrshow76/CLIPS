package com.footprint.stats.dto;

public record CategoryStatsResponse(
        CategoryInfo category,
        long count,
        double ratio
) {
    public record CategoryInfo(Long id, String name, String color, String icon) {}
}
