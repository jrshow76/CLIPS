package com.shelfy.subscription.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * subscriptions 테이블 JPA 엔티티
 * <p>
 * 해지 정책:
 * - 해지 신청 시: CANCEL_REQUESTED (현재 기간 만료까지 이용 가능)
 * - 기간 만료 후: CANCELLED (배치 처리)
 * - 해지 취소 가능: CANCEL_REQUESTED → ACTIVE
 * <p>
 * DBA 설계: (subscriber_id, item_id) 부분 UNIQUE 인덱스
 * status IN ('ACTIVE', 'CANCEL_REQUESTED') 조건으로 중복 구독 방지
 */
@Entity
@Table(name = "subscriptions")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Subscription {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long subscriberId;

    @Column(nullable = false)
    private Long itemId;

    @Column(nullable = false)
    private Long planId;

    @Column(nullable = false, length = 50)
    private String planName;

    @Column(nullable = false)
    private int amount;

    @Column(nullable = false, length = 20)
    private String paymentMethod;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private SubscriptionStatus status;

    @Column(nullable = false)
    private LocalDateTime startedAt;

    @Column(nullable = false)
    private LocalDateTime nextBillingAt;

    private LocalDateTime activeUntil;
    private LocalDateTime cancelledAt;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public Subscription(Long subscriberId, Long itemId, Long planId,
            String planName, int amount, String paymentMethod,
            LocalDateTime startedAt, LocalDateTime nextBillingAt) {
        this.subscriberId = subscriberId;
        this.itemId = itemId;
        this.planId = planId;
        this.planName = planName;
        this.amount = amount;
        this.paymentMethod = paymentMethod;
        this.status = SubscriptionStatus.ACTIVE;
        this.startedAt = startedAt;
        this.nextBillingAt = nextBillingAt;
    }

    // ===== 도메인 메서드 =====

    /**
     * 구독 해지 신청 (즉시 해지 아님, 기간 만료 후 해지)
     */
    public void requestCancel() {
        this.status = SubscriptionStatus.CANCEL_REQUESTED;
        this.cancelledAt = LocalDateTime.now();
        this.activeUntil = this.nextBillingAt.minusSeconds(1);
    }

    /**
     * 해지 취소 (재활성화) - activeUntil 이전에만 가능
     */
    public void reactivate() {
        this.status = SubscriptionStatus.ACTIVE;
        this.cancelledAt = null;
        this.activeUntil = null;
    }

    /**
     * 구독 최종 해지 (배치 처리 - 기간 만료 후)
     */
    public void cancel() {
        this.status = SubscriptionStatus.CANCELLED;
    }

    public boolean isActive() {
        return status == SubscriptionStatus.ACTIVE;
    }

    public boolean isCancelRequested() {
        return status == SubscriptionStatus.CANCEL_REQUESTED;
    }

    public boolean isOwnedBy(Long userId) {
        return this.subscriberId.equals(userId);
    }

    public enum SubscriptionStatus {
        ACTIVE, CANCEL_REQUESTED, CANCELLED
    }
}
