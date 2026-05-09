package com.shelfy.item.dto.request;

import com.shelfy.item.entity.Item;
import com.shelfy.item.entity.SubscriptionPlan;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

@Getter
@NoArgsConstructor
public class CreateItemRequest {

    @NotBlank(message = "상품명을 입력하세요.")
    @Size(min = 2, max = 100, message = "상품명은 2~100자여야 합니다.")
    private String title;

    @NotBlank(message = "상품 설명을 입력하세요.")
    @Size(min = 10, max = 5000, message = "상품 설명은 10~5000자여야 합니다.")
    private String description;

    @NotNull(message = "카테고리를 선택하세요.")
    private Item.ItemCategory category;

    @NotNull(message = "판매 유형을 선택하세요.")
    private Item.SaleType saleType;

    private Integer price;

    @Valid
    private List<SubscriptionPlanRequest> subscriptionPlans;

    private List<Long> imageIds;

    private Integer thumbnailIndex;

    @Size(max = 10, message = "태그는 최대 10개까지 등록 가능합니다.")
    private List<String> tags;

    private Item.ItemStatus status;

    @Getter
    @NoArgsConstructor
    public static class SubscriptionPlanRequest {

        @NotBlank(message = "플랜명을 입력하세요.")
        @Size(min = 2, max = 50, message = "플랜명은 2~50자여야 합니다.")
        private String planName;

        @NotNull(message = "구독 기간을 선택하세요.")
        private SubscriptionPlan.PlanPeriod period;

        @NotNull(message = "구독 가격을 입력하세요.")
        @Min(value = 100, message = "구독 가격은 100원 이상이어야 합니다.")
        private Integer planPrice;

        @Size(max = 500, message = "플랜 설명은 500자 이하여야 합니다.")
        private String description;
    }
}
