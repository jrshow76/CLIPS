package com.shelfy.item.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.common.response.PageResponse;
import com.shelfy.file.entity.FileEntity;
import com.shelfy.file.repository.FileRepository;
import com.shelfy.item.dto.request.CreateItemRequest;
import com.shelfy.item.dto.request.ItemSearchCondition;
import com.shelfy.item.dto.request.UpdateItemRequest;
import com.shelfy.item.dto.response.ItemDetailResponse;
import com.shelfy.item.dto.response.ItemSummaryResponse;
import com.shelfy.item.entity.Item;
import com.shelfy.item.entity.ItemImage;
import com.shelfy.item.entity.SubscriptionPlan;
import com.shelfy.item.mapper.ItemMapper;
import com.shelfy.item.repository.ItemRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 상품 도메인 비즈니스 로직
 * <p>
 * 트랜잭션 경계:
 * - 클래스 레벨: readOnly = true (기본)
 * - 쓰기 메서드: @Transactional 별도 선언
 * <p>
 * JPA 사용: 등록/수정/삭제 (단순 CRUD)
 * MyBatis 사용: 목록 조회, 검색 (복잡한 JOIN, 동적 쿼리)
 */
@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class ItemService {

    private final ItemRepository itemRepository;
    private final FileRepository fileRepository;
    private final ItemMapper itemMapper;

    // ===== 상품 등록 =====

    /**
     * 상품 등록
     * <p>
     * 1. 이메일 인증 완료 여부 확인
     * 2. 입력 유효성 검증 (가격 범위, 구독 플랜 필수 여부)
     * 3. Item 엔티티 저장
     * 4. 이미지 연결 (ItemImage 저장)
     * 5. 구독 플랜 저장
     *
     * @param request      등록 요청
     * @param sellerId     판매자 ID
     * @param emailVerified 이메일 인증 완료 여부
     * @return itemId
     */
    @Transactional
    public Long createItem(CreateItemRequest request, Long sellerId, boolean emailVerified) {
        if (!emailVerified) {
            throw new ShelfyException(ErrorCode.EMAIL_NOT_VERIFIED);
        }

        validateItemRequest(request.getSaleType(), request.getPrice(), request.getSubscriptionPlans());

        String[] tags = toTagArray(request.getTags());

        Item item = Item.builder()
                .sellerId(sellerId)
                .title(request.getTitle())
                .description(request.getDescription())
                .category(request.getCategory())
                .saleType(request.getSaleType())
                .price(request.getPrice())
                .status(request.getStatus())
                .tags(tags)
                .build();

        itemRepository.save(item);

        // 이미지 연결
        if (request.getImageIds() != null && !request.getImageIds().isEmpty()) {
            attachImages(item, request.getImageIds(), request.getThumbnailIndex());
        }

        // 구독 플랜 저장
        if (request.getSubscriptionPlans() != null && !request.getSubscriptionPlans().isEmpty()) {
            saveSubscriptionPlans(item, request.getSubscriptionPlans());
        }

        log.info("Item created: itemId={}, sellerId={}", item.getId(), sellerId);
        return item.getId();
    }

    // ===== 상품 수정 =====

    /**
     * 상품 수정
     * <p>
     * 1. 상품 존재 확인 및 소유권 검증
     * 2. 구독자 존재하는 플랜 가격 변경 차단
     * 3. 엔티티 업데이트
     */
    @Transactional
    public Map<String, Object> updateItem(Long itemId, UpdateItemRequest request, Long sellerId) {
        Item item = getActiveItem(itemId);
        checkOwnership(item, sellerId, ErrorCode.ITEM_UPDATE_FORBIDDEN);

        // 구독 플랜 가격 변경 검증
        if (request.getSubscriptionPlans() != null) {
            validatePlanPriceChange(item, request.getSubscriptionPlans());
        }

        validateItemRequest(
                request.getSaleType() != null ? request.getSaleType() : item.getSaleType(),
                request.getPrice() != null ? request.getPrice() : item.getPrice(),
                request.getSubscriptionPlans()
        );

        String[] tags = request.getTags() != null ? toTagArray(request.getTags()) : null;

        item.update(
                request.getTitle(),
                request.getDescription(),
                request.getCategory(),
                request.getSaleType(),
                request.getPrice(),
                request.getStatus(),
                tags
        );

        // 이미지 교체
        if (request.getImageIds() != null) {
            item.getImages().clear();
            attachImages(item, request.getImageIds(), request.getThumbnailIndex());
        }

        // 구독 플랜 업데이트
        if (request.getSubscriptionPlans() != null) {
            updateSubscriptionPlans(item, request.getSubscriptionPlans());
        }

        itemRepository.save(item);

        log.info("Item updated: itemId={}, sellerId={}", itemId, sellerId);
        return Map.of("itemId", itemId, "updatedAt", LocalDateTime.now().toString());
    }

    // ===== 상품 삭제 =====

    /**
     * 상품 삭제 (소프트 삭제)
     * <p>
     * 활성 구독자 존재 시 삭제 불가
     */
    @Transactional
    public void deleteItem(Long itemId, Long sellerId) {
        Item item = getActiveItem(itemId);
        checkOwnership(item, sellerId, ErrorCode.ITEM_DELETE_FORBIDDEN);

        if (itemRepository.hasActiveSubscribers(itemId)) {
            throw new ShelfyException(ErrorCode.ACTIVE_SUBSCRIBER_EXISTS);
        }

        item.softDelete();
        itemRepository.save(item);

        log.info("Item deleted: itemId={}, sellerId={}", itemId, sellerId);
    }

    // ===== 상품 상태 변경 =====

    @Transactional
    public Map<String, Object> updateItemStatus(Long itemId, Item.ItemStatus status, Long sellerId) {
        Item item = getActiveItem(itemId);
        checkOwnership(item, sellerId, ErrorCode.ITEM_UPDATE_FORBIDDEN);

        item.updateStatus(status);
        itemRepository.save(item);

        return Map.of("itemId", itemId, "status", status.name());
    }

    // ===== 상품 목록 조회 (피드) =====

    public PageResponse<ItemSummaryResponse> getPublishedItems(ItemSearchCondition condition) {
        List<ItemSummaryResponse> content = itemMapper.findPublishedItems(condition);
        long total = itemMapper.countPublishedItems(condition);
        return buildPageResponse(content, total, condition);
    }

    // ===== 상품 검색 =====

    public PageResponse<ItemSummaryResponse> searchItems(ItemSearchCondition condition) {
        List<ItemSummaryResponse> content = itemMapper.searchItems(condition);
        long total = itemMapper.countSearchItems(condition);
        return buildPageResponse(content, total, condition);
    }

    // ===== 셀러 본인 상품 목록 =====

    public PageResponse<ItemSummaryResponse> getMyItems(ItemSearchCondition condition, Long sellerId) {
        condition.setSellerId(sellerId);
        List<ItemSummaryResponse> content = itemMapper.findMyItems(condition);
        long total = itemMapper.countMyItems(condition);
        return buildPageResponse(content, total, condition);
    }

    // ===== 상품 상세 조회 =====

    /**
     * 상품 상세 조회
     * <p>
     * DRAFT 상태 상품은 소유자만 조회 가능
     *
     * @param itemId   상품 ID
     * @param viewerId 조회자 ID (null이면 비로그인)
     */
    @Transactional
    public ItemDetailResponse getItemDetail(Long itemId, Long viewerId) {
        ItemDetailResponse detail = itemMapper.findItemDetail(itemId)
                .orElseThrow(() -> new ShelfyException(ErrorCode.BROWSE_ITEM_NOT_FOUND));

        // DRAFT 상태 접근 제어
        if ("DRAFT".equals(detail.getStatus())) {
            if (viewerId == null || !viewerId.equals(detail.getSeller().getUserId())) {
                throw new ShelfyException(ErrorCode.ITEM_PRIVATE);
            }
        }

        // 조회수 증가 (비동기 처리 권장이나 우선 동기 처리)
        itemRepository.findActiveById(itemId)
                .ifPresent(item -> {
                    item.incrementViewCount();
                    itemRepository.save(item);
                });

        return detail;
    }

    // ===== 내부 헬퍼 메서드 =====

    private Item getActiveItem(Long itemId) {
        return itemRepository.findActiveById(itemId)
                .orElseThrow(() -> new ShelfyException(ErrorCode.ITEM_NOT_FOUND));
    }

    private void checkOwnership(Item item, Long userId, ErrorCode errorCode) {
        if (!item.isOwnedBy(userId)) {
            throw new ShelfyException(errorCode);
        }
    }

    private void validateItemRequest(Item.SaleType saleType, Integer price,
            List<CreateItemRequest.SubscriptionPlanRequest> plans) {
        // 구매 상품 가격 검증
        if (saleType == Item.SaleType.PURCHASE || saleType == Item.SaleType.BOTH) {
            if (price == null || price < 100 || price > 10_000_000) {
                throw new ShelfyException(ErrorCode.PRICE_OUT_OF_RANGE);
            }
        }

        // 구독 상품 플랜 필수
        if (saleType == Item.SaleType.SUBSCRIBE || saleType == Item.SaleType.BOTH) {
            if (plans == null || plans.isEmpty()) {
                throw new ShelfyException(ErrorCode.SUBSCRIPTION_PLAN_REQUIRED);
            }
        }
    }

    private void attachImages(Item item, List<Long> imageIds, Integer thumbnailIndex) {
        int thumbIdx = thumbnailIndex != null ? thumbnailIndex : 0;
        for (int i = 0; i < imageIds.size(); i++) {
            Long fileId = imageIds.get(i);
            String imageUrl = fileRepository.findById(fileId)
                    .map(FileEntity::getCdnUrl)
                    .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));

            ItemImage image = ItemImage.builder()
                    .item(item)
                    .fileId(fileId)
                    .imageUrl(imageUrl)
                    .sortOrder(i)
                    .isThumbnail(i == thumbIdx)
                    .build();
            item.getImages().add(image);
        }
    }

    private void saveSubscriptionPlans(Item item,
            List<CreateItemRequest.SubscriptionPlanRequest> planRequests) {
        for (CreateItemRequest.SubscriptionPlanRequest pr : planRequests) {
            SubscriptionPlan plan = SubscriptionPlan.builder()
                    .item(item)
                    .planName(pr.getPlanName())
                    .period(pr.getPeriod())
                    .planPrice(pr.getPlanPrice())
                    .description(pr.getDescription())
                    .build();
            item.getSubscriptionPlans().add(plan);
        }
    }

    private void validatePlanPriceChange(Item item,
            List<CreateItemRequest.SubscriptionPlanRequest> planRequests) {
        // 기존 플랜 가격 변경 시도 여부 확인
        item.getSubscriptionPlans().forEach(existingPlan -> {
            planRequests.stream()
                    .filter(pr -> pr.getPlanName().equals(existingPlan.getPlanName())
                            && pr.getPeriod().equals(existingPlan.getPeriod())
                            && pr.getPlanPrice() != existingPlan.getPlanPrice())
                    .findFirst()
                    .ifPresent(pr -> {
                        long activeCount = itemMapper.countActiveSubscribersByPlanId(existingPlan.getId());
                        if (activeCount > 0) {
                            throw new ShelfyException(ErrorCode.PLAN_PRICE_UPDATE_FORBIDDEN);
                        }
                    });
        });
    }

    private void updateSubscriptionPlans(Item item,
            List<CreateItemRequest.SubscriptionPlanRequest> planRequests) {
        // 기존 플랜 비활성화 후 새 플랜 추가 (구독자 있는 플랜은 유지)
        item.getSubscriptionPlans().forEach(plan -> {
            boolean stillExists = planRequests.stream()
                    .anyMatch(pr -> pr.getPlanName().equals(plan.getPlanName())
                            && pr.getPeriod().equals(plan.getPeriod()));
            if (!stillExists) {
                plan.deactivate();
            }
        });

        // 신규 플랜 추가
        planRequests.stream()
                .filter(pr -> item.getSubscriptionPlans().stream()
                        .noneMatch(p -> p.getPlanName().equals(pr.getPlanName())
                                && p.getPeriod().equals(pr.getPeriod())))
                .forEach(pr -> {
                    SubscriptionPlan newPlan = SubscriptionPlan.builder()
                            .item(item)
                            .planName(pr.getPlanName())
                            .period(pr.getPeriod())
                            .planPrice(pr.getPlanPrice())
                            .description(pr.getDescription())
                            .build();
                    item.getSubscriptionPlans().add(newPlan);
                });
    }

    private String[] toTagArray(List<String> tags) {
        if (tags == null || tags.isEmpty()) {
            return new String[0];
        }
        return tags.stream()
                .filter(t -> t != null && !t.isBlank() && t.length() <= 20)
                .toArray(String[]::new);
    }

    private PageResponse<ItemSummaryResponse> buildPageResponse(
            List<ItemSummaryResponse> content, long totalElements, ItemSearchCondition condition) {
        return PageResponse.of(content, condition.getPage(), condition.getSize(), totalElements);
    }
}
