package com.shelfy.item.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

/**
 * item_images 테이블 JPA 엔티티
 * <p>
 * DBA 설계: (item_id, sort_order) UNIQUE, is_thumbnail=TRUE에 부분 UNIQUE 인덱스
 */
@Entity
@Table(name = "item_images")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ItemImage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "item_id", nullable = false)
    private Item item;

    @Column(nullable = false)
    private Long fileId;            // files.id 참조 (FK 대신 논리적 연결)

    @Column(nullable = false, length = 2048)
    private String imageUrl;

    @Column(nullable = false)
    private int sortOrder;

    @Column(nullable = false)
    private boolean isThumbnail = false;

    @Builder
    public ItemImage(Item item, Long fileId, String imageUrl, int sortOrder, boolean isThumbnail) {
        this.item = item;
        this.fileId = fileId;
        this.imageUrl = imageUrl;
        this.sortOrder = sortOrder;
        this.isThumbnail = isThumbnail;
    }

    public void setThumbnail(boolean isThumbnail) {
        this.isThumbnail = isThumbnail;
    }
}
