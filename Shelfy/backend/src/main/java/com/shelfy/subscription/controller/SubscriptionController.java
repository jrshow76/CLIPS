package com.shelfy.subscription.controller;

import com.shelfy.common.response.ApiResponse;
import com.shelfy.security.CustomUserDetails;
import com.shelfy.subscription.dto.request.CreateSubscriptionRequest;
import com.shelfy.subscription.dto.response.SubscriptionResponse;
import com.shelfy.subscription.service.SubscriptionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

/**
 * 구독 API 컨트롤러
 * <p>
 * Base URL: /api/v1/subscriptions
 */
@RestController
@RequestMapping("/api/v1/subscriptions")
@RequiredArgsConstructor
public class SubscriptionController {

    private final SubscriptionService subscriptionService;

    /**
     * POST /api/v1/subscriptions - 구독 신청
     */
    @PostMapping
    public ResponseEntity<ApiResponse<SubscriptionResponse>> createSubscription(
            @RequestBody @Valid CreateSubscriptionRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        SubscriptionResponse response = subscriptionService.createSubscription(
                request, userDetails.getUserId());
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success(response));
    }

    /**
     * POST /api/v1/subscriptions/{subscriptionId}/cancel - 구독 해지 신청
     * <p>
     * 즉시 해지가 아닌 현재 구독 기간 만료 후 해지 (CANCEL_REQUESTED 상태)
     */
    @PostMapping("/{subscriptionId}/cancel")
    public ResponseEntity<ApiResponse<SubscriptionResponse>> cancelSubscription(
            @PathVariable Long subscriptionId,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        SubscriptionResponse response = subscriptionService.cancelSubscription(
                subscriptionId, userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * POST /api/v1/subscriptions/{subscriptionId}/reactivate - 구독 해지 취소 (재활성화)
     * <p>
     * CANCEL_REQUESTED → ACTIVE (만료 기간 이전에만 가능)
     */
    @PostMapping("/{subscriptionId}/reactivate")
    public ResponseEntity<ApiResponse<SubscriptionResponse>> reactivateSubscription(
            @PathVariable Long subscriptionId,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        SubscriptionResponse response = subscriptionService.reactivateSubscription(
                subscriptionId, userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
