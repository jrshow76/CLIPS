package com.shelfy.item.mapper;

import com.shelfy.item.dto.request.ItemSearchCondition;
import com.shelfy.item.dto.response.ItemDetailResponse;
import com.shelfy.item.dto.response.ItemSummaryResponse;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Optional;

/**
 * 상품 MyBatis Mapper
 * <p>
 * JPA로 처리하기 어려운 복잡한 쿼리를 담당한다:
 * - 다중 JOIN 목록 조회 (seller 정보 포함)
 * - tsvector 전문 검색
 * - 동적 정렬/필터 조건
 * - COUNT 집계 (페이지네이션용)
 */
@Mapper
public interface ItemMapper {

    /**
     * 상품 피드 목록 조회 (PUBLISHED 상태, 동적 필터/정렬)
     * 대상 쿼리 패턴: ITEM-Q1, ITEM-Q2, ITEM-Q3
     */
    List<ItemSummaryResponse> findPublishedItems(ItemSearchCondition condition);

    /**
     * 상품 피드 목록 전체 건수 (페이지네이션용)
     */
    long countPublishedItems(ItemSearchCondition condition);

    /**
     * 전문 검색 (tsvector @@ to_tsquery)
     * 대상 쿼리 패턴: ITEM-Q4
     */
    List<ItemSummaryResponse> searchItems(ItemSearchCondition condition);

    /**
     * 전문 검색 결과 전체 건수
     */
    long countSearchItems(ItemSearchCondition condition);

    /**
     * 셀러 본인 상품 목록 조회 (동적 status 필터, 정렬)
     * 대상 쿼리 패턴: ITEM-Q5
     */
    List<ItemSummaryResponse> findMyItems(ItemSearchCondition condition);

    /**
     * 셀러 본인 상품 목록 전체 건수
     */
    long countMyItems(ItemSearchCondition condition);

    /**
     * 상품 상세 조회 (seller 정보, 이미지, 구독 플랜 포함)
     * 대상 쿼리 패턴: ITEM-Q7 (JOIN 포함)
     */
    Optional<ItemDetailResponse> findItemDetail(@Param("itemId") Long itemId);

    /**
     * 특정 플랜에 활성 구독자 수 조회
     * 상품 수정 시 planPrice 변경 가능 여부 확인용
     */
    long countActiveSubscribersByPlanId(@Param("planId") Long planId);
}
