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
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

/**
 * 셀러 대시보드 / 공개 프로필 서비스
 * <p>
 * 집계 쿼리는 MyBatis SellerMapper를 통해 처리한다.
 * 클래스 레벨 readOnly = true 적용 (쓰기 작업 없음).
 */
@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class SellerService {

    private static final double PLATFORM_FEE_RATE = 0.10;
    private static final int DEFAULT_PROFILE_ITEM_SIZE = 12;

    private final SellerMapper sellerMapper;
    private final UserRepository userRepository;

    /**
     * 셀러 판매 통계 조회 (대시보드)
     *
     * @param sellerId 셀러 ID (JWT에서 추출)
     * @return 판매 통계 응답 DTO
     */
    public SellerStatsResponse getSellerStats(Long sellerId) {
        long totalRevenue = sellerMapper.sumCompletedOrderAmount(sellerId);
        long totalOrderCount = sellerMapper.countCompletedOrders(sellerId);
        long activeSubscriberCount = sellerMapper.countActiveSubscribers(sellerId);

        long totalFee = Math.round(totalRevenue * PLATFORM_FEE_RATE);
        long netRevenue = totalRevenue - totalFee;

        return SellerStatsResponse.builder()
                .totalRevenue(totalRevenue)
                .totalOrderCount(totalOrderCount)
                .activeSubscriberCount(activeSubscriberCount)
                .totalFee(totalFee)
                .netRevenue(netRevenue)
                .build();
    }

    /**
     * 월별 수익 현황 조회 (대시보드)
     *
     * @param sellerId 셀러 ID
     * @param year     조회 연도 (기본값: 현재 연도)
     * @return 월별 수익 응답 DTO
     */
    public MonthlyRevenueResponse getMonthlyRevenue(Long sellerId, Integer year) {
        int targetYear = (year != null) ? year : LocalDate.now().getYear();

        List<MonthlyRevenueResponse.MonthlyRevenue> monthlyRevenue =
                sellerMapper.selectMonthlyRevenue(sellerId, targetYear);

        long totalRevenue = monthlyRevenue.stream()
                .mapToLong(MonthlyRevenueResponse.MonthlyRevenue::getRevenue)
                .sum();
        long totalFee = Math.round(totalRevenue * PLATFORM_FEE_RATE);
        long netRevenue = totalRevenue - totalFee;

        return MonthlyRevenueResponse.builder()
                .year(targetYear)
                .totalRevenue(totalRevenue)
                .totalFee(totalFee)
                .netRevenue(netRevenue)
                .monthlyRevenue(monthlyRevenue)
                .build();
    }

    /**
     * 셀러 공개 프로필 조회 (닉네임 기반)
     *
     * @param nickname 셀러 닉네임
     * @param page     페이지 번호 (0-based)
     * @param size     페이지당 항목 수
     * @return 셀러 공개 프로필 + 상품 목록
     */
    public SellerPublicProfileResponse getSellerPublicProfile(
            String nickname, int page, int size) {

        User seller = userRepository.findActiveByNickname(nickname)
                .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));

        int itemCount = sellerMapper.countPublishedItems(seller.getId());
        long subscriberCount = sellerMapper.countTotalSubscribers(seller.getId());

        int offset = page * size;
        List<SellerPublicProfileResponse.SellerItemSummary> items =
                sellerMapper.selectPublishedItems(seller.getId(), offset, size);

        PageResponse<SellerPublicProfileResponse.SellerItemSummary> itemPage =
                PageResponse.of(items, page, size, itemCount);

        return SellerPublicProfileResponse.of(seller, itemCount, subscriberCount, itemPage);
    }
}
