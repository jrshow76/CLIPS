package com.shelfy.seller.mapper;

import com.shelfy.seller.dto.MonthlyRevenueResponse;
import com.shelfy.seller.dto.SellerPublicProfileResponse;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 셀러 대시보드 MyBatis Mapper
 * <p>
 * 집계 쿼리(SUM, COUNT, GROUP BY)는 MyBatis로 처리한다.
 * SQL Injection 방지를 위해 반드시 #{} 바인딩을 사용한다.
 */
@Mapper
public interface SellerMapper {

    /**
     * 셀러별 총 판매액 조회 (COMPLETED 상태 주문만 집계)
     *
     * @param sellerId 셀러 ID
     * @return 총 판매액 (원 단위)
     */
    long sumCompletedOrderAmount(@Param("sellerId") Long sellerId);

    /**
     * 셀러별 완료 주문 수 조회
     *
     * @param sellerId 셀러 ID
     * @return 완료 주문 수
     */
    long countCompletedOrders(@Param("sellerId") Long sellerId);

    /**
     * 셀러별 활성 구독자 수 조회 (ACTIVE 상태)
     *
     * @param sellerId 셀러 ID
     * @return 활성 구독자 수
     */
    long countActiveSubscribers(@Param("sellerId") Long sellerId);

    /**
     * 연도별 월별 수익 집계 (GROUP BY month)
     *
     * @param sellerId 셀러 ID
     * @param year     조회 연도 (예: 2026)
     * @return 월별 수익 목록
     */
    List<MonthlyRevenueResponse.MonthlyRevenue> selectMonthlyRevenue(
            @Param("sellerId") Long sellerId,
            @Param("year") int year);

    /**
     * 셀러의 PUBLISHED 상품 수 조회 (공개 프로필용)
     *
     * @param sellerId 셀러 ID
     * @return 공개 상품 수
     */
    int countPublishedItems(@Param("sellerId") Long sellerId);

    /**
     * 셀러의 PUBLISHED 상품 목록 조회 (공개 프로필용, 페이지네이션)
     *
     * @param sellerId 셀러 ID
     * @param offset   오프셋
     * @param limit    조회 수
     * @return 상품 요약 목록
     */
    List<SellerPublicProfileResponse.SellerItemSummary> selectPublishedItems(
            @Param("sellerId") Long sellerId,
            @Param("offset") int offset,
            @Param("limit") int limit);

    /**
     * 셀러 전체 구독자 수 조회 (공개 프로필용)
     *
     * @param sellerId 셀러 ID
     * @return 전체 구독자 수
     */
    long countTotalSubscribers(@Param("sellerId") Long sellerId);
}
