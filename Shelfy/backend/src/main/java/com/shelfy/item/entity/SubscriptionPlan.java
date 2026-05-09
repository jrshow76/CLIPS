package com.shelfy.item.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * subscription_plans 테이블 JPA 엔티티
 * <p>
 * 구독자가 존재하는 플랜의 planPrice는 변경 불가 (비즈니스 정책).
 * DBA 설계: (item_id, period, plan_name) UNIQUE 제약조건 적용.
 */
@Entity
@Table(name = "subscription_plans")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SubscriptionPlan {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "item_id", nullable = false)
    private Item item;

    @Column(nullable = false, length = 50)
    private String planName;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private PlanPeriod period;

    @Column(nullable = false)
    private int planPrice;

    @Column(length = 500)
    private String description;

    @Column(nullable = false)
    private boolean isActive = true;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public SubscriptionPlan(Item item, String planName, PlanPeriod period,
            int planPrice, String description) {
        this.item = item;
        this.planName = planName;
        this.period = period;
        this.planPrice = planPrice;
        this.description = description;
    }

    /** 플랜 비활성화 (구독자 존재 시 삭제 대신 비활성화) */
    public void deactivate() {
        this.isActive = false;
    }

    public enum PlanPeriod {
        MONTHLY, QUARTERLY, YEARLY
    }
}
