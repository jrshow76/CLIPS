package com.shelfy.item.dto.request;

import com.shelfy.item.entity.Item;
import com.shelfy.item.entity.SubscriptionPlan;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 상품 수정 요청 DTO
 * <p>
 * 변경할 필드만 포함 가능 (null이면 변경하지 않음).
 */
@Getter
@NoArgsConstructor
public class UpdateItemRequest {

    @Size(min = 2, max = 100, message = "상품명은 2~100자여야 합니다.")
    private String title;

    @Size(min = 10, max = 5000, message = "상품 설명은 10~5000자여야 합니다.")
    private String description;

    private Item.ItemCategory category;
    private Item.SaleType saleType;
    private Integer price;

    private List<CreateItemRequest.SubscriptionPlanRequest> subscriptionPlans;
    private List<Long> imageIds;
    private Integer thumbnailIndex;

    @Size(max = 10, message = "태그는 최대 10개까지 등록 가능합니다.")
    private List<String> tags;

    private Item.ItemStatus status;
}
