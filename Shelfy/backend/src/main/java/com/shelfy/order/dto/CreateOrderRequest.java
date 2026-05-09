package com.shelfy.order.dto;

import com.shelfy.order.entity.Order;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class CreateOrderRequest {

    @NotNull(message = "상품 ID는 필수입니다.")
    private Long itemId;

    @NotNull(message = "결제 수단은 필수입니다.")
    private Order.PaymentMethod paymentMethod;
}
