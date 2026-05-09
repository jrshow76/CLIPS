package com.shelfy.seller.dto;

import com.shelfy.common.response.PageResponse;
import com.shelfy.user.entity.User;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 셀러 공개 프로필 응답 DTO
 * <p>
 * API 스펙: GET /api/v1/users/{nickname}/profile
 * 공개 상품 목록(PUBLISHED)을 페이지네이션으로 함께 반환한다.
 */
@Getter
@Builder
public class SellerPublicProfileResponse {

    private Long userId;
    private String nickname;
    private String bio;
    private String profileImageUrl;
    private int itemCount;
    private long subscriberCount;
    private LocalDateTime joinedAt;
    private PageResponse<SellerItemSummary> items;

    public static SellerPublicProfileResponse of(User user, int itemCount,
            long subscriberCount, PageResponse<SellerItemSummary> items) {
        return SellerPublicProfileResponse.builder()
                .userId(user.getId())
                .nickname(user.getNickname())
                .bio(user.getBio())
                .profileImageUrl(user.getProfileImageUrl())
                .itemCount(itemCount)
                .subscriberCount(subscriberCount)
                .joinedAt(user.getCreatedAt())
                .items(items)
                .build();
    }

    /**
     * 셀러 공개 프로필에 포함되는 상품 요약 정보
     */
    @Getter
    @Builder
    public static class SellerItemSummary {
        private Long itemId;
        private String title;
        private Integer price;
        private String saleType;
        private String thumbnailUrl;
    }
}
