package com.shelfy.order.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * orders 테이블 JPA 엔티티
 * <p>
 * 주문 시점의 상품명·가격을 스냅샷으로 저장한다.
 * 상품이 삭제되거나 가격이 변경되어도 구매 당시 내역이 보존된다.
 * 소프트 삭제 없이 상태(OrderStatus)로만 관리한다.
 */
@Entity
@Table(name = "orders")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 구매자 ID */
    @Column(nullable = false)
    private Long buyerId;

    /** 셀러 ID (정산 처리용) */
    @Column(nullable = false)
    private Long sellerId;

    /** 상품 ID (FK, 상품이 삭제되어도 주문 내역은 유지) */
    @Column(nullable = false)
    private Long itemId;

    /** 상품명 스냅샷 (주문 시점 저장) */
    @Column(nullable = false, length = 100)
    private String itemTitle;

    /** 결제 금액 스냅샷 (주문 시점 저장) */
    @Column(nullable = false)
    private int amount;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PaymentMethod paymentMethod;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OrderStatus status;

    /** 결제 완료 시각 */
    private LocalDateTime paidAt;

    /** 환불 완료 시각 */
    private LocalDateTime refundedAt;

    /** 환불 요청 사유 */
    @Column(length = 500)
    private String refundReason;

    /** 콘텐츠 열람(다운로드) 여부 */
    @Column(nullable = false)
    private boolean contentAccessed = false;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public Order(Long buyerId, Long sellerId, Long itemId, String itemTitle,
            int amount, PaymentMethod paymentMethod) {
        this.buyerId = buyerId;
        this.sellerId = sellerId;
        this.itemId = itemId;
        this.itemTitle = itemTitle;
        this.amount = amount;
        this.paymentMethod = paymentMethod;
        this.status = OrderStatus.COMPLETED;
        this.paidAt = LocalDateTime.now();
    }

    // ===== 도메인 메서드 =====

    /** 환불 처리 */
    public void refund(String reason) {
        this.status = OrderStatus.REFUNDED;
        this.refundedAt = LocalDateTime.now();
        this.refundReason = reason;
    }

    /** 콘텐츠 열람 처리 */
    public void markContentAccessed() {
        this.contentAccessed = true;
    }

    /** 환불 가능 여부 검증 (7일 이내, 미열람) */
    public boolean isRefundable() {
        if (this.status != OrderStatus.COMPLETED) {
            return false;
        }
        if (this.contentAccessed) {
            return false;
        }
        return this.paidAt != null
                && LocalDateTime.now().isBefore(this.paidAt.plusDays(7));
    }

    // ===== Enum 정의 =====

    public enum PaymentMethod {
        CARD, KAKAO_PAY, NAVER_PAY
    }

    public enum OrderStatus {
        COMPLETED, REFUNDED, CANCELLED
    }
}
