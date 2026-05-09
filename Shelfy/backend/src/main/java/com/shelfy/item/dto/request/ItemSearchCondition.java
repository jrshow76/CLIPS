package com.shelfy.item.dto.request;

import com.shelfy.item.entity.Item;
import lombok.Getter;
import lombok.Setter;

/**
 * 상품 목록 조회 / 검색 조건 DTO
 * <p>
 * @ModelAttribute 바인딩용으로 @Setter 허용.
 * MyBatis ItemMapper에 그대로 전달된다.
 */
@Getter
@Setter
public class ItemSearchCondition {

    // 검색 키워드 (전문 검색)
    private String q;

    // 필터
    private Item.ItemCategory category;
    private Item.SaleType saleType;
    private Integer minPrice;
    private Integer maxPrice;

    // 정렬: latest / popular / lowPrice / highPrice (피드용)
    //       createdAt / title / price (셀러 목록용)
    private String sort = "latest";
    private String order = "DESC";

    // 페이지네이션
    private int page = 0;
    private int size = 20;

    // 셀러 목록 조회용
    private Long sellerId;
    private Item.ItemStatus status;  // 셀러 목록 필터 (ALL 포함)

    public int getOffset() {
        return page * size;
    }
}
