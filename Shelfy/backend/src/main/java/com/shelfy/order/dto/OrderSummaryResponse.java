package com.shelfy.order.dto;

import com.shelfy.order.entity.Order;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@Builder
public class OrderSummaryResponse {

    private Long orderId;
    private String itemTitle;
    private int amount;
    private LocalDateTime paidAt;
    private Order.OrderStatus status;

    public static OrderSummaryResponse from(Order order) {
        return OrderSummaryResponse.builder()
                .orderId(order.getId())
                .itemTitle(order.getItemTitle())
                .amount(order.getAmount())
                .paidAt(order.getPaidAt())
                .status(order.getStatus())
                .build();
    }
}
