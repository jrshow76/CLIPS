package com.footprint.stats.dto;

public record MonthlyStatsResponse(
        int year,
        int month,
        long count
) {}
