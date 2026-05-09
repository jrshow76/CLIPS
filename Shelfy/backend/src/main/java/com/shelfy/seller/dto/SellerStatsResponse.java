package com.shelfy.seller.dto;

import lombok.Builder;
import lombok.Getter;

/**
 * 셀러 대시보드 판매 통계 응답 DTO
 * <p>
 * API 스펙: GET /api/v1/seller/stats
 */
@Getter
@Builder
public class SellerStatsResponse {

    /** 총 판매액 (환불 완료 주문 제외) */
    private long totalRevenue;

    /** 총 주문 수 (완료 상태) */
    private long totalOrderCount;

    /** 현재 활성 구독자 수 */
    private long activeSubscriberCount;

    /** 플랫폼 수수료 (10%) */
    private long totalFee;

    /** 순수익 (totalRevenue - totalFee) */
    private long netRevenue;
}
