package com.shelfy.seller.controller;

import com.shelfy.common.response.ApiResponse;
import com.shelfy.security.CustomUserDetails;
import com.shelfy.seller.dto.MonthlyRevenueResponse;
import com.shelfy.seller.dto.SellerPublicProfileResponse;
import com.shelfy.seller.dto.SellerStatsResponse;
import com.shelfy.seller.service.SellerService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

/**
 * 셀러 대시보드 및 공개 프로필 API 컨트롤러
 * <p>
 * Controller에서 Repository 또는 Mapper 직접 호출 금지.
 * 모든 비즈니스 로직은 SellerService에 위임한다.
 */
@RestController
@RequiredArgsConstructor
public class SellerController {

    private final SellerService sellerService;

    /**
     * GET /api/v1/seller/stats
     * 셀러 판매 통계 (총 판매액, 주문 수, 활성 구독자 수)
     * 인증 필요: Bearer Token
     */
    @GetMapping("/api/v1/seller/stats")
    public ResponseEntity<ApiResponse<SellerStatsResponse>> getSellerStats(
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        SellerStatsResponse response = sellerService.getSellerStats(userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * GET /api/v1/seller/revenue?year={year}
     * 셀러 월별 수익 현황
     * 인증 필요: Bearer Token
     */
    @GetMapping("/api/v1/seller/revenue")
    public ResponseEntity<ApiResponse<MonthlyRevenueResponse>> getMonthlyRevenue(
            @RequestParam(required = false) Integer year,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        MonthlyRevenueResponse response = sellerService.getMonthlyRevenue(
                userDetails.getUserId(), year);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * GET /api/v1/users/{nickname}/profile
     * 셀러 공개 프로필 + 상품 목록
     * 인증 불필요: 전체 공개
     */
    @GetMapping("/api/v1/users/{nickname}/profile")
    public ResponseEntity<ApiResponse<SellerPublicProfileResponse>> getSellerPublicProfile(
            @PathVariable String nickname,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "12") int size) {

        SellerPublicProfileResponse response = sellerService.getSellerPublicProfile(
                nickname, page, size);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
