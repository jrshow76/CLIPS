package com.shelfy.order.dto;

import com.shelfy.order.entity.Order;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@Builder
public class RefundResponse {

    private Long orderId;
    private Order.OrderStatus status;
    private int refundAmount;
    private LocalDateTime refundedAt;

    public static RefundResponse from(Order order) {
        return RefundResponse.builder()
                .orderId(order.getId())
                .status(order.getStatus())
                .refundAmount(order.getAmount())
                .refundedAt(order.getRefundedAt())
                .build();
    }
}
