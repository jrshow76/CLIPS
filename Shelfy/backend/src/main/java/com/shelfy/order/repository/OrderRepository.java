package com.shelfy.order.repository;

import com.shelfy.order.entity.Order;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDateTime;

public interface OrderRepository extends JpaRepository<Order, Long> {

    /**
     * 구매자 주문 목록 조회 (날짜 필터 없음)
     */
    Page<Order> findByBuyerIdOrderByCreatedAtDesc(Long buyerId, Pageable pageable);

    /**
     * 구매자 주문 목록 조회 (날짜 범위 필터)
     */
    @Query("SELECT o FROM Order o WHERE o.buyerId = :buyerId " +
           "AND o.paidAt >= :startDate AND o.paidAt < :endDate " +
           "ORDER BY o.createdAt DESC")
    Page<Order> findByBuyerIdAndPaidAtBetween(
            @Param("buyerId") Long buyerId,
            @Param("startDate") LocalDateTime startDate,
            @Param("endDate") LocalDateTime endDate,
            Pageable pageable);

    /**
     * 셀러별 완료 주문 수 (대시보드 통계용)
     */
    @Query("SELECT COUNT(o) FROM Order o WHERE o.sellerId = :sellerId " +
           "AND o.status = com.shelfy.order.entity.Order.OrderStatus.COMPLETED")
    long countCompletedBySellerId(@Param("sellerId") Long sellerId);

    /**
     * 셀러별 총 판매액 (대시보드 통계용)
     */
    @Query("SELECT COALESCE(SUM(o.amount), 0) FROM Order o WHERE o.sellerId = :sellerId " +
           "AND o.status = com.shelfy.order.entity.Order.OrderStatus.COMPLETED")
    long sumAmountBySellerId(@Param("sellerId") Long sellerId);
}
