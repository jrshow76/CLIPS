package com.shelfy.subscription.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@Builder
@AllArgsConstructor
public class SubscriptionResponse {

    private Long subscriptionId;
    private Long itemId;
    private String itemTitle;
    private String planName;
    private String period;
    private int amount;
    private String status;
    private LocalDateTime startedAt;
    private LocalDateTime nextBillingAt;
    private LocalDateTime cancelledAt;
    private LocalDateTime activeUntil;
}
