package com.shelfy.order.controller;

import com.shelfy.common.response.ApiResponse;
import com.shelfy.common.response.PageResponse;
import com.shelfy.order.dto.CreateOrderRequest;
import com.shelfy.order.dto.CreateOrderResponse;
import com.shelfy.order.dto.OrderSummaryResponse;
import com.shelfy.order.dto.RefundRequest;
import com.shelfy.order.dto.RefundResponse;
import com.shelfy.order.service.OrderService;
import com.shelfy.security.CustomUserDetails;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

/**
 * 주문(구매) API 컨트롤러
 * <p>
 * Controller에서 Repository 직접 호출 금지.
 * 모든 비즈니스 로직은 OrderService에 위임한다.
 */
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderService orderService;

    /**
     * POST /api/v1/orders
     * 단일 구매 주문 생성
     */
    @PostMapping
    public ResponseEntity<ApiResponse<CreateOrderResponse>> createOrder(
            @RequestBody @Valid CreateOrderRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        CreateOrderResponse response = orderService.createOrder(request, userDetails.getUserId());
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success(response));
    }

    /**
     * GET /api/v1/orders
     * 구매 내역 목록 조회 (페이지네이션, 날짜 필터)
     */
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<OrderSummaryResponse>>> getOrders(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        PageResponse<OrderSummaryResponse> response = orderService.getOrders(
                userDetails.getUserId(), page, size, startDate, endDate);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * GET /api/v1/orders/{orderId}
     * 주문 상세 조회
     */
    @GetMapping("/{orderId}")
    public ResponseEntity<ApiResponse<CreateOrderResponse>> getOrderDetail(
            @PathVariable Long orderId,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        CreateOrderResponse response = orderService.getOrderDetail(orderId, userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * POST /api/v1/orders/{orderId}/cancel
     * 환불(취소) 요청
     */
    @PostMapping("/{orderId}/cancel")
    public ResponseEntity<ApiResponse<RefundResponse>> refundOrder(
            @PathVariable Long orderId,
            @RequestBody @Valid RefundRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        RefundResponse response = orderService.refundOrder(orderId, request, userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
