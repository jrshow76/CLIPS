package com.shelfy.order.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.common.response.PageResponse;
import com.shelfy.item.entity.Item;
import com.shelfy.item.repository.ItemRepository;
import com.shelfy.order.dto.CreateOrderRequest;
import com.shelfy.order.dto.CreateOrderResponse;
import com.shelfy.order.dto.OrderSummaryResponse;
import com.shelfy.order.dto.RefundRequest;
import com.shelfy.order.dto.RefundResponse;
import com.shelfy.order.entity.Order;
import com.shelfy.order.repository.OrderRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 주문(구매) 서비스
 * <p>
 * 클래스 레벨 readOnly = true 적용.
 * 쓰기 작업 메서드에만 @Transactional 별도 선언.
 */
@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class OrderService {

    private final OrderRepository orderRepository;
    private final ItemRepository itemRepository;

    /**
     * 단일 구매 주문 생성
     *
     * @param request  구매 요청 DTO
     * @param buyerId  구매자 ID (JWT에서 추출)
     * @return 생성된 주문 응답 DTO
     */
    @Transactional
    public CreateOrderResponse createOrder(CreateOrderRequest request, Long buyerId) {
        Item item = itemRepository.findById(request.getItemId())
                .orElseThrow(() -> new ShelfyException(ErrorCode.ORDER_ITEM_UNAVAILABLE));

        // 삭제되거나 비공개 상품은 구매 불가
        if (item.isDeleted() || item.getStatus() != Item.ItemStatus.PUBLISHED) {
            throw new ShelfyException(ErrorCode.ORDER_ITEM_UNAVAILABLE);
        }

        // 본인 상품 구매 불가
        if (item.isOwnedBy(buyerId)) {
            throw new ShelfyException(ErrorCode.SELF_PURCHASE);
        }

        // 구독 전용 상품은 단건 구매 불가
        if (item.getSaleType() == Item.SaleType.SUBSCRIBE) {
            throw new ShelfyException(ErrorCode.SUBSCRIBE_ONLY_ITEM);
        }

        // 가격이 없는 경우 결제 불가 (데이터 정합성 오류)
        if (item.getPrice() == null) {
            throw new ShelfyException(ErrorCode.PAYMENT_FAILED);
        }

        Order order = Order.builder()
                .buyerId(buyerId)
                .sellerId(item.getSellerId())
                .itemId(item.getId())
                .itemTitle(item.getTitle())
                .amount(item.getPrice())
                .paymentMethod(request.getPaymentMethod())
                .build();

        Order savedOrder = orderRepository.save(order);
        log.info("주문 생성 완료: orderId={}, buyerId={}, itemId={}",
                savedOrder.getId(), buyerId, item.getId());

        return CreateOrderResponse.from(savedOrder);
    }

    /**
     * 구매 내역 목록 조회 (날짜 필터 지원)
     *
     * @param buyerId   구매자 ID
     * @param page      페이지 번호 (0-based)
     * @param size      페이지당 항목 수
     * @param startDate 조회 시작일 (nullable)
     * @param endDate   조회 종료일 (nullable)
     * @return 페이지네이션 형식의 주문 요약 목록
     */
    public PageResponse<OrderSummaryResponse> getOrders(
            Long buyerId, int page, int size,
            LocalDate startDate, LocalDate endDate) {

        Pageable pageable = PageRequest.of(page, size);
        Page<Order> orders;

        if (startDate != null && endDate != null) {
            LocalDateTime startDateTime = startDate.atStartOfDay();
            LocalDateTime endDateTime = endDate.plusDays(1).atStartOfDay();
            orders = orderRepository.findByBuyerIdAndPaidAtBetween(
                    buyerId, startDateTime, endDateTime, pageable);
        } else {
            orders = orderRepository.findByBuyerIdOrderByCreatedAtDesc(buyerId, pageable);
        }

        Page<OrderSummaryResponse> responsePage = orders.map(OrderSummaryResponse::from);
        return PageResponse.of(responsePage);
    }

    /**
     * 주문 상세 조회
     *
     * @param orderId 주문 ID
     * @param buyerId 요청자 ID (본인 확인용)
     * @return 주문 상세 DTO
     */
    public CreateOrderResponse getOrderDetail(Long orderId, Long buyerId) {
        Order order = findOrderByIdAndBuyerId(orderId, buyerId);
        return CreateOrderResponse.from(order);
    }

    /**
     * 환불(취소) 요청
     *
     * @param orderId  주문 ID
     * @param request  환불 요청 DTO
     * @param buyerId  요청자 ID (본인 확인용)
     * @return 환불 결과 DTO
     */
    @Transactional
    public RefundResponse refundOrder(Long orderId, RefundRequest request, Long buyerId) {
        Order order = findOrderByIdAndBuyerId(orderId, buyerId);

        // 콘텐츠 열람 이력 존재 확인
        if (order.isContentAccessed()) {
            throw new ShelfyException(ErrorCode.CONTENT_ACCESSED);
        }

        // 환불 기간(7일) 초과 확인
        if (!order.isRefundable()) {
            // 이미 환불된 경우와 기간 초과를 구분하여 처리
            if (order.getStatus() == Order.OrderStatus.REFUNDED) {
                throw new ShelfyException(ErrorCode.REFUND_PERIOD_EXPIRED);
            }
            throw new ShelfyException(ErrorCode.REFUND_PERIOD_EXPIRED);
        }

        order.refund(request.getReason());
        log.info("환불 처리 완료: orderId={}, buyerId={}, reason={}",
                orderId, buyerId, request.getReason());

        return RefundResponse.from(order);
    }

    // ===== private 헬퍼 메서드 =====

    private Order findOrderByIdAndBuyerId(Long orderId, Long buyerId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));

        if (!order.getBuyerId().equals(buyerId)) {
            throw new ShelfyException(ErrorCode.FORBIDDEN);
        }
        return order;
    }
}
