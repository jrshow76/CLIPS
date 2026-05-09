package com.shelfy.seller.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.common.response.PageResponse;
import com.shelfy.seller.dto.MonthlyRevenueResponse;
import com.shelfy.seller.dto.SellerPublicProfileResponse;
import com.shelfy.seller.dto.SellerStatsResponse;
import com.shelfy.seller.mapper.SellerMapper;
import com.shelfy.user.entity.User;
import com.shelfy.user.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
@DisplayName("SellerService 단위 테스트")
class SellerServiceTest {

    @InjectMocks
    private SellerService sellerService;

    @Mock
    private SellerMapper sellerMapper;

    @Mock
    private UserRepository userRepository;

    // ===== getSellerStats 테스트 =====

    @Test
    @DisplayName("셀러 통계 조회 - 수수료 및 순수익 계산 정확성")
    void getSellerStats_feeCalculation() {
        // given
        Long sellerId = 1L;
        given(sellerMapper.sumCompletedOrderAmount(sellerId)).willReturn(1_000_000L);
        given(sellerMapper.countCompletedOrders(sellerId)).willReturn(50L);
        given(sellerMapper.countActiveSubscribers(sellerId)).willReturn(30L);

        // when
        SellerStatsResponse stats = sellerService.getSellerStats(sellerId);

        // then
        assertThat(stats.getTotalRevenue()).isEqualTo(1_000_000L);
        assertThat(stats.getTotalOrderCount()).isEqualTo(50L);
        assertThat(stats.getActiveSubscriberCount()).isEqualTo(30L);
        assertThat(stats.getTotalFee()).isEqualTo(100_000L);      // 10%
        assertThat(stats.getNetRevenue()).isEqualTo(900_000L);    // 90%
    }

    @Test
    @DisplayName("셀러 통계 조회 - 판매 내역 없을 때 0 반환")
    void getSellerStats_noSales_returnsZero() {
        // given
        Long sellerId = 1L;
        given(sellerMapper.sumCompletedOrderAmount(sellerId)).willReturn(0L);
        given(sellerMapper.countCompletedOrders(sellerId)).willReturn(0L);
        given(sellerMapper.countActiveSubscribers(sellerId)).willReturn(0L);

        // when
        SellerStatsResponse stats = sellerService.getSellerStats(sellerId);

        // then
        assertThat(stats.getTotalRevenue()).isZero();
        assertThat(stats.getTotalFee()).isZero();
        assertThat(stats.getNetRevenue()).isZero();
    }

    // ===== getMonthlyRevenue 테스트 =====

    @Test
    @DisplayName("월별 수익 조회 - 특정 연도 지정")
    void getMonthlyRevenue_withYear() {
        // given
        Long sellerId = 1L;
        int year = 2026;
        List<MonthlyRevenueResponse.MonthlyRevenue> monthly = List.of(
                buildMonthlyRevenue("2026-01", 300_000L),
                buildMonthlyRevenue("2026-02", 500_000L)
        );

        given(sellerMapper.selectMonthlyRevenue(sellerId, year)).willReturn(monthly);

        // when
        MonthlyRevenueResponse response = sellerService.getMonthlyRevenue(sellerId, year);

        // then
        assertThat(response.getYear()).isEqualTo(2026);
        assertThat(response.getTotalRevenue()).isEqualTo(800_000L);
        assertThat(response.getTotalFee()).isEqualTo(80_000L);      // 10%
        assertThat(response.getNetRevenue()).isEqualTo(720_000L);
        assertThat(response.getMonthlyRevenue()).hasSize(2);
    }

    @Test
    @DisplayName("월별 수익 조회 - year 미지정 시 현재 연도 사용")
    void getMonthlyRevenue_withoutYear_usesCurrentYear() {
        // given
        Long sellerId = 1L;
        int currentYear = java.time.LocalDate.now().getYear();
        given(sellerMapper.selectMonthlyRevenue(sellerId, currentYear)).willReturn(List.of());

        // when
        MonthlyRevenueResponse response = sellerService.getMonthlyRevenue(sellerId, null);

        // then
        assertThat(response.getYear()).isEqualTo(currentYear);
        assertThat(response.getMonthlyRevenue()).isEmpty();
        assertThat(response.getTotalRevenue()).isZero();
    }

    // ===== getSellerPublicProfile 테스트 =====

    @Test
    @DisplayName("셀러 공개 프로필 조회 - 정상 케이스")
    void getSellerPublicProfile_success() {
        // given
        String nickname = "testSeller";
        User seller = buildUser(1L, "seller@example.com", nickname);

        given(userRepository.findActiveByNickname(nickname)).willReturn(Optional.of(seller));
        given(sellerMapper.countPublishedItems(1L)).willReturn(5);
        given(sellerMapper.countTotalSubscribers(1L)).willReturn(20L);
        given(sellerMapper.selectPublishedItems(1L, 0, 12)).willReturn(List.of());

        // when
        SellerPublicProfileResponse response = sellerService.getSellerPublicProfile(nickname, 0, 12);

        // then
        assertThat(response.getNickname()).isEqualTo(nickname);
        assertThat(response.getItemCount()).isEqualTo(5);
        assertThat(response.getSubscriberCount()).isEqualTo(20L);
        assertThat(response.getItems()).isNotNull();
    }

    @Test
    @DisplayName("존재하지 않는 닉네임으로 공개 프로필 조회 - RESOURCE_NOT_FOUND 예외 발생")
    void getSellerPublicProfile_nicknameNotFound_throwsException() {
        // given
        String nickname = "nonExistentNick";
        given(userRepository.findActiveByNickname(nickname)).willReturn(Optional.empty());

        // when & then
        assertThatThrownBy(() -> sellerService.getSellerPublicProfile(nickname, 0, 12))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.RESOURCE_NOT_FOUND);
    }

    @Test
    @DisplayName("공개 프로필 상품 목록 페이지네이션 확인")
    void getSellerPublicProfile_pagination() {
        // given
        String nickname = "paginationSeller";
        User seller = buildUser(1L, "seller@example.com", nickname);
        List<SellerPublicProfileResponse.SellerItemSummary> items = List.of(
                buildItemSummary(1L, "상품1"),
                buildItemSummary(2L, "상품2")
        );

        given(userRepository.findActiveByNickname(nickname)).willReturn(Optional.of(seller));
        given(sellerMapper.countPublishedItems(1L)).willReturn(25);
        given(sellerMapper.countTotalSubscribers(1L)).willReturn(10L);
        given(sellerMapper.selectPublishedItems(1L, 0, 12)).willReturn(items);

        // when
        SellerPublicProfileResponse response = sellerService.getSellerPublicProfile(nickname, 0, 12);

        // then
        PageResponse<SellerPublicProfileResponse.SellerItemSummary> itemPage = response.getItems();
        assertThat(itemPage.getContent()).hasSize(2);
        assertThat(itemPage.getTotalElements()).isEqualTo(25);
        assertThat(itemPage.getTotalPages()).isEqualTo(3); // ceil(25/12)
        assertThat(itemPage.isFirst()).isTrue();
    }

    // ===== 테스트 픽스처 헬퍼 메서드 =====

    private User buildUser(Long userId, String email, String nickname) {
        return User.builder()
                .email(email)
                .passwordHash("인코딩된비밀번호")
                .nickname(nickname)
                .agreeTerms(true)
                .agreePrivacy(true)
                .agreeMarketing(false)
                .build();
    }

    private MonthlyRevenueResponse.MonthlyRevenue buildMonthlyRevenue(String month, long revenue) {
        return MonthlyRevenueResponse.MonthlyRevenue.builder()
                .month(month)
                .revenue(revenue)
                .fee(revenue / 10)
                .netRevenue(revenue - revenue / 10)
                .build();
    }

    private SellerPublicProfileResponse.SellerItemSummary buildItemSummary(Long itemId, String title) {
        return SellerPublicProfileResponse.SellerItemSummary.builder()
                .itemId(itemId)
                .title(title)
                .price(10000)
                .saleType("PURCHASE")
                .thumbnailUrl("https://cdn.shelfy.io/images/test.jpg")
                .build();
    }
}
