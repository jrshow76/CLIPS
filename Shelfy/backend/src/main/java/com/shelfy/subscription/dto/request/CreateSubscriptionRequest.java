package com.shelfy.subscription.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class CreateSubscriptionRequest {

    @NotNull(message = "상품 ID를 입력하세요.")
    private Long itemId;

    @NotNull(message = "구독 플랜 ID를 입력하세요.")
    private Long planId;

    @NotBlank(message = "결제 수단을 선택하세요.")
    private String paymentMethod;
}
