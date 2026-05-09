package com.shelfy.item.repository;

import com.shelfy.item.entity.Item;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface ItemRepository extends JpaRepository<Item, Long> {

    /**
     * 상품 상세 조회 (삭제된 상품 제외)
     */
    @Query("SELECT i FROM Item i WHERE i.id = :id AND i.deletedAt IS NULL")
    Optional<Item> findActiveById(@Param("id") Long id);

    /**
     * 활성 구독자 존재 여부 확인 (상품 삭제 가능 여부 체크)
     * Native Query로 Subscription 테이블 직접 참조 (순환 의존성 방지)
     */
    @Query(value = """
            SELECT COUNT(*) > 0
            FROM subscriptions s
            WHERE s.item_id = :itemId
              AND s.status IN ('ACTIVE', 'CANCEL_REQUESTED')
            """, nativeQuery = true)
    boolean hasActiveSubscribers(@Param("itemId") Long itemId);
}
