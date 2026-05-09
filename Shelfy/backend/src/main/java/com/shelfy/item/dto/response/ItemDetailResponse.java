package com.shelfy.item.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 상품 상세 조회 응답 DTO
 * MyBatis ResultMap으로 매핑된다.
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ItemDetailResponse {

    private Long itemId;
    private String title;
    private String description;
    private String category;
    private String saleType;
    private Integer price;
    private String status;
    private long viewCount;

    private List<SubscriptionPlanDto> subscriptionPlans;
    private List<ImageDto> images;
    private List<String> tags;

    private SellerDto seller;

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SubscriptionPlanDto {
        private Long planId;
        private String planName;
        private String period;
        private int planPrice;
        private String description;
    }

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ImageDto {
        private Long imageId;
        private String url;
        private boolean isThumbnail;
    }

    @Getter
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SellerDto {
        private Long userId;
        private String nickname;
        private String profileImageUrl;
        private int itemCount;
    }
}
