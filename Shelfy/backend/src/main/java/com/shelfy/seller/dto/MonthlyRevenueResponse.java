package com.shelfy.seller.dto;

import lombok.Builder;
import lombok.Getter;

import java.util.List;

/**
 * 셀러 월별 수익 응답 DTO
 * <p>
 * API 스펙: GET /api/v1/seller/revenue?year={year}
 */
@Getter
@Builder
public class MonthlyRevenueResponse {

    private int year;
    private long totalRevenue;
    private long totalFee;
    private long netRevenue;
    private List<MonthlyRevenue> monthlyRevenue;

    @Getter
    @Builder
    public static class MonthlyRevenue {
        /** 월 표시 (예: "2026-01") */
        private String month;
        private long revenue;
        private long fee;
        private long netRevenue;
    }
}
