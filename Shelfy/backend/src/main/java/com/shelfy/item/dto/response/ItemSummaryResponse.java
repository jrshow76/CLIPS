package com.shelfy.item.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 상품 목록 조회 응답 DTO (피드, 검색, 셀러 목록)
 * MyBatis ResultMap으로 매핑된다.
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ItemSummaryResponse {

    private Long itemId;
    private String title;
    private Integer price;
    private String saleType;
    private String status;
    private String thumbnailUrl;
    private LocalDateTime createdAt;

    // 셀러 정보 (피드 조회 시 포함)
    private String sellerNickname;
}
