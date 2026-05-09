package com.shelfy.subscription.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.item.entity.Item;
import com.shelfy.item.entity.SubscriptionPlan;
import com.shelfy.item.repository.ItemRepository;
import com.shelfy.subscription.dto.request.CreateSubscriptionRequest;
import com.shelfy.subscription.dto.response.SubscriptionResponse;
import com.shelfy.subscription.entity.Subscription;
import com.shelfy.subscription.entity.SubscriptionPayment;
import com.shelfy.subscription.repository.SubscriptionPaymentRepository;
import com.shelfy.subscription.repository.SubscriptionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 구독 도메인 비즈니스 로직
 * <p>
 * 구독 해지 정책:
 * - 해지 신청: CANCEL_REQUESTED 상태로 변경, 기간 만료 후 CANCELLED
 * - 해지 취소(재활성화): CANCEL_REQUESTED → ACTIVE (만료 전까지만 가능)
 * <p>
 * 트랜잭션 경계:
 * - 구독 생성: 결제 + 구독 레코드 생성을 단일 트랜잭션으로 처리
 */
@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class SubscriptionService {

    private final SubscriptionRepository subscriptionRepository;
    private final SubscriptionPaymentRepository paymentRepository;
    private final ItemRepository itemRepository;

    // ===== 구독 신청 =====

    /**
     * 구독 신청 처리
     * <p>
     * 1. 상품 존재 및 구독 지원 여부 확인
     * 2. 본인 상품 구독 차단
     * 3. 이미 활성 구독 존재 여부 확인
     * 4. 결제 처리 (Stub - 실제 PG 연동은 별도 모듈)
     * 5. 구독 레코드 + 결제 레코드 저장
     */
    @Transactional
    public SubscriptionResponse createSubscription(CreateSubscriptionRequest request,
            Long subscriberId) {
        Item item = itemRepository.findActiveById(request.getItemId())
                .orElseThrow(() -> new ShelfyException(ErrorCode.ORDER_ITEM_UNAVAILABLE));

        // 구독 지원 여부 확인
        if (item.getSaleType() == Item.SaleType.PURCHASE) {
            throw new ShelfyException(ErrorCode.SUBSCRIPTION_NOT_SUPPORTED);
        }

        // 본인 상품 구독 차단
        if (item.isOwnedBy(subscriberId)) {
            throw new ShelfyException(ErrorCode.SELF_SUBSCRIPTION);
        }

        // 이미 활성 구독 확인
        if (subscriptionRepository.existsActiveSubscription(subscriberId, request.getItemId())) {
            throw new ShelfyException(ErrorCode.ALREADY_SUBSCRIBED);
        }

        // 구독 플랜 조회 (N+1 방지: 이미 로드된 collection 사용)
        SubscriptionPlan plan = item.getSubscriptionPlans().stream()
                .filter(p -> p.getId().equals(request.getPlanId()) && p.isActive())
                .findFirst()
                .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));

        // 결제 처리 (Stub: 실제 PG 연동 구현 필요)
        String pgTransactionId = processPayment(request.getPaymentMethod(), plan.getPlanPrice());

        // 다음 결제일 계산
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime nextBillingAt = calculateNextBillingDate(now, plan.getPeriod());

        // 구독 레코드 저장
        Subscription subscription = Subscription.builder()
                .subscriberId(subscriberId)
                .itemId(item.getId())
                .planId(plan.getId())
                .planName(plan.getPlanName())
                .amount(plan.getPlanPrice())
                .paymentMethod(request.getPaymentMethod())
                .startedAt(now)
                .nextBillingAt(nextBillingAt)
                .build();

        subscriptionRepository.save(subscription);

        // 결제 레코드 저장
        SubscriptionPayment payment = SubscriptionPayment.builder()
                .subscriptionId(subscription.getId())
                .amount(plan.getPlanPrice())
                .billingAt(now)
                .build();
        payment.complete(pgTransactionId);
        paymentRepository.save(payment);

        log.info("Subscription created: subscriptionId={}, subscriberId={}, itemId={}",
                subscription.getId(), subscriberId, item.getId());

        return SubscriptionResponse.builder()
                .subscriptionId(subscription.getId())
                .itemId(item.getId())
                .itemTitle(item.getTitle())
                .planName(plan.getPlanName())
                .period(plan.getPeriod().name())
                .amount(plan.getPlanPrice())
                .status(subscription.getStatus().name())
                .startedAt(subscription.getStartedAt())
                .nextBillingAt(subscription.getNextBillingAt())
                .build();
    }

    // ===== 구독 해지 신청 =====

    /**
     * 구독 해지 신청 (즉시 해지 아님)
     * <p>
     * 상태: ACTIVE → CANCEL_REQUESTED
     * 기간 만료 후 배치에서 CANCELLED로 변경
     */
    @Transactional
    public SubscriptionResponse cancelSubscription(Long subscriptionId, Long subscriberId) {
        Subscription subscription = subscriptionRepository
                .findByIdAndSubscriberId(subscriptionId, subscriberId)
                .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));

        if (!subscription.isActive()) {
            throw new ShelfyException(ErrorCode.INVALID_INPUT);
        }

        subscription.requestCancel();
        subscriptionRepository.save(subscription);

        log.info("Subscription cancel requested: subscriptionId={}, subscriberId={}",
                subscriptionId, subscriberId);

        return SubscriptionResponse.builder()
                .subscriptionId(subscription.getId())
                .status(subscription.getStatus().name())
                .cancelledAt(subscription.getCancelledAt())
                .activeUntil(subscription.getActiveUntil())
                .build();
    }

    // ===== 구독 해지 취소 (재활성화) =====

    /**
     * 구독 해지 취소 - CANCEL_REQUESTED → ACTIVE
     * activeUntil(= nextBillingAt 전날) 이전까지만 가능
     */
    @Transactional
    public SubscriptionResponse reactivateSubscription(Long subscriptionId, Long subscriberId) {
        Subscription subscription = subscriptionRepository
                .findByIdAndSubscriberId(subscriptionId, subscriberId)
                .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));

        if (!subscription.isCancelRequested()) {
            throw new ShelfyException(ErrorCode.INVALID_INPUT);
        }

        // activeUntil 이후에는 재활성화 불가
        if (subscription.getActiveUntil() != null
                && LocalDateTime.now().isAfter(subscription.getActiveUntil())) {
            throw new ShelfyException(ErrorCode.INVALID_INPUT);
        }

        subscription.reactivate();
        subscriptionRepository.save(subscription);

        log.info("Subscription reactivated: subscriptionId={}, subscriberId={}",
                subscriptionId, subscriberId);

        return SubscriptionResponse.builder()
                .subscriptionId(subscription.getId())
                .status(subscription.getStatus().name())
                .build();
    }

    // ===== 내부 헬퍼 =====

    /**
     * 다음 결제일 계산
     */
    private LocalDateTime calculateNextBillingDate(LocalDateTime from,
            SubscriptionPlan.PlanPeriod period) {
        return switch (period) {
            case MONTHLY -> from.plusMonths(1);
            case QUARTERLY -> from.plusMonths(3);
            case YEARLY -> from.plusYears(1);
        };
    }

    /**
     * 결제 처리 Stub
     * 실제 구현: 카카오페이/네이버페이 등 PG사 SDK 연동
     *
     * @return pgTransactionId
     */
    private String processPayment(String paymentMethod, int amount) {
        // TODO: 실제 PG 연동 구현 필요
        // 결제 실패 시 ShelfyException(ErrorCode.SUBSCRIPTION_PAYMENT_FAILED) throw
        log.debug("Payment processed (stub): method={}, amount={}", paymentMethod, amount);
        return "PG-" + System.currentTimeMillis();
    }
}
