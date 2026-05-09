package com.shelfy.subscription.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * subscription_payments 테이블 JPA 엔티티
 * <p>
 * 구독 정기결제 내역을 관리한다.
 * DBA 설계: pg_transaction_id에 UNIQUE 제약조건 (이중 결제 방지)
 */
@Entity
@Table(name = "subscription_payments")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SubscriptionPayment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long subscriptionId;

    @Column(nullable = false)
    private int amount;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PaymentStatus status;

    @Column(unique = true, length = 100)
    private String pgTransactionId;    // 결제 대행사 트랜잭션 ID

    @Column(nullable = false)
    private LocalDateTime billingAt;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public SubscriptionPayment(Long subscriptionId, int amount,
            LocalDateTime billingAt) {
        this.subscriptionId = subscriptionId;
        this.amount = amount;
        this.status = PaymentStatus.PENDING;
        this.billingAt = billingAt;
    }

    public void complete(String pgTransactionId) {
        this.status = PaymentStatus.COMPLETED;
        this.pgTransactionId = pgTransactionId;
    }

    public void fail() {
        this.status = PaymentStatus.FAILED;
    }

    public enum PaymentStatus {
        PENDING, COMPLETED, FAILED
    }
}
