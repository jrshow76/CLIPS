package com.footprint.stats.controller;

import com.footprint.common.response.ApiResponse;
import com.footprint.stats.dto.CategoryStatsResponse;
import com.footprint.stats.dto.MonthlyStatsResponse;
import com.footprint.stats.dto.StatsSummaryResponse;
import com.footprint.stats.service.StatsService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/stats")
@RequiredArgsConstructor
public class StatsController {

    private final StatsService statsService;

    /**
     * S-01: 요약 통계 — 전체 장소 수, 이번 달, 평균 평점, 최다 카테고리
     */
    @GetMapping("/summary")
    public ApiResponse<StatsSummaryResponse> getSummary(
            @AuthenticationPrincipal UUID userId) {
        return ApiResponse.ok(statsService.getSummary(userId));
    }

    /**
     * S-02: 월별 방문 수 통계 (최근 N개월, 기본 12개월, 최대 24개월)
     */
    @GetMapping("/monthly")
    public ApiResponse<List<MonthlyStatsResponse>> getMonthlyStats(
            @AuthenticationPrincipal UUID userId,
            @RequestParam(defaultValue = "12") int months) {
        return ApiResponse.ok(statsService.getMonthlyStats(userId, months));
    }

    /**
     * S-03: 카테고리별 분포 통계
     */
    @GetMapping("/categories")
    public ApiResponse<List<CategoryStatsResponse>> getCategoryStats(
            @AuthenticationPrincipal UUID userId) {
        return ApiResponse.ok(statsService.getCategoryStats(userId));
    }
}
