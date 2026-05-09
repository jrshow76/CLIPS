package com.shelfy.item.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * items 테이블 JPA 엔티티
 * <p>
 * 태그는 PostgreSQL 배열 타입(VARCHAR[])으로 관리한다. (ADR-004)
 * 소프트 삭제(deleted_at) 방식을 사용한다.
 * 상태 변경은 도메인 메서드로만 수행한다.
 */
@Entity
@Table(name = "items")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Item {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long sellerId;

    @Column(nullable = false, length = 100)
    private String title;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private ItemCategory category;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private SaleType saleType;

    private Integer price;   // SUBSCRIBE 전용인 경우 null 가능

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private ItemStatus status;

    @Column(nullable = false)
    private long viewCount = 0L;

    /**
     * PostgreSQL 배열 타입으로 태그 저장.
     * Hibernate는 기본적으로 배열 타입을 지원하지 않으므로 String 배열로 매핑.
     * 복잡한 배열 쿼리는 MyBatis로 처리한다.
     */
    @Column(columnDefinition = "VARCHAR(20)[]")
    private String[] tags;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(nullable = false)
    private LocalDateTime updatedAt;

    private LocalDateTime deletedAt;

    /**
     * N+1 방지: FetchType.LAZY + @BatchSize 또는 JOIN FETCH 사용
     * 상품 상세 조회 시에는 MyBatis로 직접 처리하여 N+1 완전 방지
     */
    @OneToMany(mappedBy = "item", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @OrderBy("sortOrder ASC")
    private List<ItemImage> images = new ArrayList<>();

    @OneToMany(mappedBy = "item", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<SubscriptionPlan> subscriptionPlans = new ArrayList<>();

    @Builder
    public Item(Long sellerId, String title, String description, ItemCategory category,
            SaleType saleType, Integer price, ItemStatus status, String[] tags) {
        this.sellerId = sellerId;
        this.title = title;
        this.description = description;
        this.category = category;
        this.saleType = saleType;
        this.price = price;
        this.status = (status != null) ? status : ItemStatus.DRAFT;
        this.tags = tags;
    }

    // ===== 도메인 메서드 =====

    public void updateStatus(ItemStatus status) {
        this.status = status;
    }

    public void update(String title, String description, ItemCategory category,
            SaleType saleType, Integer price, ItemStatus status, String[] tags) {
        if (title != null) this.title = title;
        if (description != null) this.description = description;
        if (category != null) this.category = category;
        if (saleType != null) this.saleType = saleType;
        if (price != null) this.price = price;
        if (status != null) this.status = status;
        if (tags != null) this.tags = tags;
    }

    public void softDelete() {
        this.deletedAt = LocalDateTime.now();
        this.status = ItemStatus.DELETED;
    }

    public boolean isDeleted() {
        return deletedAt != null;
    }

    public boolean isOwnedBy(Long userId) {
        return this.sellerId.equals(userId);
    }

    public void incrementViewCount() {
        this.viewCount++;
    }

    // ===== Enum 정의 =====

    public enum ItemCategory {
        DIGITAL_CONTENT, COURSE, TEMPLATE, PHOTO, MUSIC, SOFTWARE, OTHER
    }

    public enum SaleType {
        PURCHASE, SUBSCRIBE, BOTH
    }

    public enum ItemStatus {
        DRAFT, PUBLISHED, DELETED
    }
}
