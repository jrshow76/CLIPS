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
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
@DisplayName("OrderService 단위 테스트")
class OrderServiceTest {

    @InjectMocks
    private OrderService orderService;

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private ItemRepository itemRepository;

    // ===== createOrder 테스트 =====

    @Test
    @DisplayName("정상 구매 주문 생성 - PURCHASE 타입 상품")
    void createOrder_success() {
        // given
        Long buyerId = 1L;
        Long sellerId = 2L;
        Long itemId = 100L;

        Item item = buildItem(itemId, sellerId, Item.SaleType.PURCHASE, Item.ItemStatus.PUBLISHED, 15000);
        CreateOrderRequest request = new CreateOrderRequest(itemId, Order.PaymentMethod.CARD);
        Order savedOrder = buildOrder(1L, buyerId, sellerId, itemId, 15000);

        given(itemRepository.findById(itemId)).willReturn(Optional.of(item));
        given(orderRepository.save(any(Order.class))).willReturn(savedOrder);

        // when
        CreateOrderResponse response = orderService.createOrder(request, buyerId);

        // then
        assertThat(response.getOrderId()).isEqualTo(1L);
        assertThat(response.getItemTitle()).isEqualTo("테스트 상품");
        assertThat(response.getAmount()).isEqualTo(15000);
        assertThat(response.getPaymentMethod()).isEqualTo(Order.PaymentMethod.CARD);
        verify(orderRepository).save(any(Order.class));
    }

    @Test
    @DisplayName("BOTH 타입 상품도 단건 구매 가능")
    void createOrder_bothSaleType_success() {
        // given
        Long buyerId = 1L;
        Long itemId = 100L;
        Item item = buildItem(itemId, 2L, Item.SaleType.BOTH, Item.ItemStatus.PUBLISHED, 15000);
        CreateOrderRequest request = new CreateOrderRequest(itemId, Order.PaymentMethod.CARD);
        Order savedOrder = buildOrder(1L, buyerId, 2L, itemId, 15000);

        given(itemRepository.findById(itemId)).willReturn(Optional.of(item));
        given(orderRepository.save(any(Order.class))).willReturn(savedOrder);

        // when
        CreateOrderResponse response = orderService.createOrder(request, buyerId);

        // then
        assertThat(response).isNotNull();
        assertThat(response.getStatus()).isEqualTo(Order.OrderStatus.COMPLETED);
    }

    @Test
    @DisplayName("본인 상품 구매 시도 - ORDER-E001 예외 발생")
    void createOrder_selfPurchase_throwsException() {
        // given
        Long userId = 1L;
        Long itemId = 100L;
        Item item = buildItem(itemId, userId, Item.SaleType.PURCHASE, Item.ItemStatus.PUBLISHED, 15000);
        CreateOrderRequest request = new CreateOrderRequest(itemId, Order.PaymentMethod.CARD);

        given(itemRepository.findById(itemId)).willReturn(Optional.of(item));

        // when & then
        assertThatThrownBy(() -> orderService.createOrder(request, userId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.SELF_PURCHASE);
    }

    @Test
    @DisplayName("구독 전용 상품 단건 구매 시도 - ORDER-E004 예외 발생")
    void createOrder_subscribeOnlyItem_throwsException() {
        // given
        Long buyerId = 1L;
        Long itemId = 100L;
        Item item = buildItem(itemId, 2L, Item.SaleType.SUBSCRIBE, Item.ItemStatus.PUBLISHED, null);
        CreateOrderRequest request = new CreateOrderRequest(itemId, Order.PaymentMethod.CARD);

        given(itemRepository.findById(itemId)).willReturn(Optional.of(item));

        // when & then
        assertThatThrownBy(() -> orderService.createOrder(request, buyerId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.SUBSCRIBE_ONLY_ITEM);
    }

    @Test
    @DisplayName("존재하지 않는 상품 구매 시도 - ORDER-E002 예외 발생")
    void createOrder_itemNotFound_throwsException() {
        // given
        Long buyerId = 1L;
        Long itemId = 999L;
        CreateOrderRequest request = new CreateOrderRequest(itemId, Order.PaymentMethod.CARD);

        given(itemRepository.findById(itemId)).willReturn(Optional.empty());

        // when & then
        assertThatThrownBy(() -> orderService.createOrder(request, buyerId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.ORDER_ITEM_UNAVAILABLE);
    }

    @Test
    @DisplayName("비공개(DRAFT) 상품 구매 시도 - ORDER-E002 예외 발생")
    void createOrder_draftItem_throwsException() {
        // given
        Long buyerId = 1L;
        Long itemId = 100L;
        Item item = buildItem(itemId, 2L, Item.SaleType.PURCHASE, Item.ItemStatus.DRAFT, 10000);
        CreateOrderRequest request = new CreateOrderRequest(itemId, Order.PaymentMethod.CARD);

        given(itemRepository.findById(itemId)).willReturn(Optional.of(item));

        // when & then
        assertThatThrownBy(() -> orderService.createOrder(request, buyerId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.ORDER_ITEM_UNAVAILABLE);
    }

    // ===== getOrders 테스트 =====

    @Test
    @DisplayName("구매 내역 목록 조회 - 날짜 필터 없음")
    void getOrders_withoutDateFilter_success() {
        // given
        Long buyerId = 1L;
        Order order = buildOrder(1L, buyerId, 2L, 100L, 15000);
        PageImpl<Order> page = new PageImpl<>(List.of(order), PageRequest.of(0, 20), 1);

        given(orderRepository.findByBuyerIdOrderByCreatedAtDesc(buyerId, PageRequest.of(0, 20)))
                .willReturn(page);

        // when
        PageResponse<OrderSummaryResponse> response =
                orderService.getOrders(buyerId, 0, 20, null, null);

        // then
        assertThat(response.getContent()).hasSize(1);
        assertThat(response.getTotalElements()).isEqualTo(1);
        assertThat(response.isFirst()).isTrue();
        assertThat(response.isLast()).isTrue();
    }

    @Test
    @DisplayName("주문 상세 조회 - 정상 케이스")
    void getOrderDetail_success() {
        // given
        Long buyerId = 1L;
        Long orderId = 1L;
        Order order = buildOrder(orderId, buyerId, 2L, 100L, 15000);

        given(orderRepository.findById(orderId)).willReturn(Optional.of(order));

        // when
        CreateOrderResponse response = orderService.getOrderDetail(orderId, buyerId);

        // then
        assertThat(response.getItemTitle()).isEqualTo("테스트 상품");
        assertThat(response.getAmount()).isEqualTo(15000);
    }

    @Test
    @DisplayName("타인 주문 상세 조회 시도 - FORBIDDEN 예외 발생")
    void getOrderDetail_otherUserOrder_throwsException() {
        // given
        Long requesterId = 1L;
        Long actualBuyerId = 2L;
        Long orderId = 1L;
        Order order = buildOrder(orderId, actualBuyerId, 3L, 100L, 15000);

        given(orderRepository.findById(orderId)).willReturn(Optional.of(order));

        // when & then
        assertThatThrownBy(() -> orderService.getOrderDetail(orderId, requesterId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.FORBIDDEN);
    }

    // ===== refundOrder 테스트 =====

    @Test
    @DisplayName("환불 성공 - 7일 이내, 미열람")
    void refundOrder_success() {
        // given
        Long buyerId = 1L;
        Long orderId = 1L;
        Order order = buildOrder(orderId, buyerId, 2L, 100L, 15000);
        RefundRequest request = new RefundRequest("단순 변심");

        given(orderRepository.findById(orderId)).willReturn(Optional.of(order));

        // when
        RefundResponse response = orderService.refundOrder(orderId, request, buyerId);

        // then
        assertThat(response.getOrderId()).isEqualTo(orderId);
        assertThat(response.getStatus()).isEqualTo(Order.OrderStatus.REFUNDED);
        assertThat(response.getRefundAmount()).isEqualTo(15000);
        assertThat(response.getRefundedAt()).isNotNull();
    }

    @Test
    @DisplayName("타인 주문 환불 시도 - FORBIDDEN 예외 발생")
    void refundOrder_otherUserOrder_throwsException() {
        // given
        Long requesterId = 1L;
        Long actualBuyerId = 2L;
        Long orderId = 1L;
        Order order = buildOrder(orderId, actualBuyerId, 3L, 100L, 15000);
        RefundRequest request = new RefundRequest("단순 변심");

        given(orderRepository.findById(orderId)).willReturn(Optional.of(order));

        // when & then
        assertThatThrownBy(() -> orderService.refundOrder(orderId, request, requesterId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.FORBIDDEN);
    }

    @Test
    @DisplayName("콘텐츠 열람 이력 있는 주문 환불 시도 - ORDER-E011 예외 발생")
    void refundOrder_contentAccessed_throwsException() {
        // given
        Long buyerId = 1L;
        Long orderId = 1L;
        Order order = buildOrder(orderId, buyerId, 2L, 100L, 15000);
        order.markContentAccessed();
        RefundRequest request = new RefundRequest("단순 변심");

        given(orderRepository.findById(orderId)).willReturn(Optional.of(order));

        // when & then
        assertThatThrownBy(() -> orderService.refundOrder(orderId, request, buyerId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.CONTENT_ACCESSED);
    }

    @Test
    @DisplayName("존재하지 않는 주문 환불 시도 - RESOURCE_NOT_FOUND 예외 발생")
    void refundOrder_orderNotFound_throwsException() {
        // given
        Long buyerId = 1L;
        Long orderId = 999L;
        RefundRequest request = new RefundRequest("단순 변심");

        given(orderRepository.findById(orderId)).willReturn(Optional.empty());

        // when & then
        assertThatThrownBy(() -> orderService.refundOrder(orderId, request, buyerId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.RESOURCE_NOT_FOUND);
    }

    // ===== Order 도메인 로직 테스트 =====

    @Test
    @DisplayName("Order.isRefundable() - 생성 직후 환불 가능")
    void order_isRefundable_justCreated() {
        // given
        Order order = buildOrder(1L, 1L, 2L, 100L, 15000);

        // when & then
        assertThat(order.isRefundable()).isTrue();
    }

    @Test
    @DisplayName("Order.isRefundable() - 콘텐츠 열람 후 환불 불가")
    void order_isRefundable_afterContentAccess() {
        // given
        Order order = buildOrder(1L, 1L, 2L, 100L, 15000);
        order.markContentAccessed();

        // when & then
        assertThat(order.isRefundable()).isFalse();
    }

    // ===== 테스트 픽스처 헬퍼 메서드 =====

    private Item buildItem(Long itemId, Long sellerId, Item.SaleType saleType,
            Item.ItemStatus status, Integer price) {
        return Item.builder()
                .sellerId(sellerId)
                .title("테스트 상품")
                .description("테스트 상품 설명입니다.")
                .category(Item.ItemCategory.TEMPLATE)
                .saleType(saleType)
                .price(price)
                .status(status)
                .tags(new String[]{"태그1"})
                .build();
    }

    private Order buildOrder(Long orderId, Long buyerId, Long sellerId,
            Long itemId, int amount) {
        return Order.builder()
                .buyerId(buyerId)
                .sellerId(sellerId)
                .itemId(itemId)
                .itemTitle("테스트 상품")
                .amount(amount)
                .paymentMethod(Order.PaymentMethod.CARD)
                .build();
    }
}
