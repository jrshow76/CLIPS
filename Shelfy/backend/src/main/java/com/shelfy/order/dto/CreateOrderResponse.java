package com.shelfy.order.dto;

import com.shelfy.order.entity.Order;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@Builder
public class CreateOrderResponse {

    private Long orderId;
    private Long itemId;
    private String itemTitle;
    private int amount;
    private Order.PaymentMethod paymentMethod;
    private Order.OrderStatus status;
    private LocalDateTime paidAt;

    public static CreateOrderResponse from(Order order) {
        return CreateOrderResponse.builder()
                .orderId(order.getId())
                .itemId(order.getItemId())
                .itemTitle(order.getItemTitle())
                .amount(order.getAmount())
                .paymentMethod(order.getPaymentMethod())
                .status(order.getStatus())
                .paidAt(order.getPaidAt())
                .build();
    }
}
