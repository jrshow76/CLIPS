package com.shelfy.subscription.repository;

import com.shelfy.subscription.entity.Subscription;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface SubscriptionRepository extends JpaRepository<Subscription, Long> {

    /**
     * 활성 구독 중복 확인 (구독 신청 전 체크)
     * DBA 설계: uq_subscriptions_active_per_user_item 부분 UNIQUE 인덱스와 일치
     */
    @Query("""
            SELECT COUNT(s) > 0
            FROM Subscription s
            WHERE s.subscriberId = :subscriberId
              AND s.itemId = :itemId
              AND s.status IN ('ACTIVE', 'CANCEL_REQUESTED')
            """)
    boolean existsActiveSubscription(@Param("subscriberId") Long subscriberId,
            @Param("itemId") Long itemId);

    /**
     * 소유자 확인을 포함한 구독 조회
     */
    @Query("SELECT s FROM Subscription s WHERE s.id = :id AND s.subscriberId = :subscriberId")
    Optional<Subscription> findByIdAndSubscriberId(@Param("id") Long id,
            @Param("subscriberId") Long subscriberId);
}
