package com.footprint.stats.service;

import com.footprint.category.entity.Category;
import com.footprint.category.repository.CategoryRepository;
import com.footprint.place.repository.PlaceRepository;
import com.footprint.stats.dto.CategoryStatsResponse;
import com.footprint.stats.dto.MonthlyStatsResponse;
import com.footprint.stats.dto.StatsSummaryResponse;
import com.footprint.stats.dto.StatsSummaryResponse.TopCategoryDto;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class StatsService {

    private final PlaceRepository placeRepository;
    private final CategoryRepository categoryRepository;

    /**
     * 요약 통계: 전체 장소 수, 이번 달 방문 수, 평균 평점, 최다 카테고리
     */
    public StatsSummaryResponse getSummary(UUID userId) {
        long totalPlaces = placeRepository.countByUser_IdAndDeletedAtIsNull(userId);
        long thisMonthPlaces = placeRepository.countThisMonth(userId);
        Double avgRating = placeRepository.avgRating(userId);

        TopCategoryDto topCategory = resolveTopCategory(userId);

        return new StatsSummaryResponse(totalPlaces, thisMonthPlaces, avgRating, topCategory);
    }

    /**
     * 월별 방문 수 통계 (최근 N개월, 기본 12개월)
     */
    public List<MonthlyStatsResponse> getMonthlyStats(UUID userId, int months) {
        int limitMonths = Math.min(months, 24);
        List<Object[]> rows = placeRepository.countByMonth(userId);

        return rows.stream()
                .limit(limitMonths)
                .map(row -> {
                    // DATE_TRUNC 결과는 DB 드라이버에 따라 Timestamp 또는 LocalDateTime 반환
                    LocalDateTime ym = toLocalDateTime(row[0]);
                    long count = ((Number) row[1]).longValue();
                    return new MonthlyStatsResponse(ym.getYear(), ym.getMonthValue(), count);
                })
                .toList();
    }

    /**
     * 카테고리별 분포 통계 (비율 포함)
     */
    public List<CategoryStatsResponse> getCategoryStats(UUID userId) {
        List<Object[]> rows = categoryRepository.countPlacesByCategory(userId);

        if (rows.isEmpty()) {
            return List.of();
        }

        // 전체 장소 수 합산 (비율 계산용)
        long total = rows.stream()
                .mapToLong(row -> ((Number) row[1]).longValue())
                .sum();

        // 카테고리 메타 정보 일괄 조회
        List<Long> categoryIds = rows.stream()
                .map(row -> (Long) row[0])
                .toList();
        Map<Long, Category> categoryMap = categoryRepository.findAllById(categoryIds)
                .stream()
                .collect(Collectors.toMap(Category::getId, c -> c));

        return rows.stream()
                .filter(row -> categoryMap.containsKey((Long) row[0]))
                .map(row -> {
                    Long catId = (Long) row[0];
                    long count = ((Number) row[1]).longValue();
                    Category cat = categoryMap.get(catId);
                    double ratio = total > 0
                            ? Math.round((double) count / total * 1000.0) / 10.0
                            : 0.0;
                    return new CategoryStatsResponse(
                            new CategoryStatsResponse.CategoryInfo(catId, cat.getName(), cat.getColor(), cat.getIcon()),
                            count,
                            ratio
                    );
                })
                .sorted(Comparator.comparingLong(CategoryStatsResponse::count).reversed())
                .toList();
    }

    // -------------------------------------------------------------------------
    // private helpers
    // -------------------------------------------------------------------------

    private TopCategoryDto resolveTopCategory(UUID userId) {
        List<Object[]> rows = categoryRepository.countPlacesByCategory(userId);
        if (rows.isEmpty()) {
            return null;
        }

        Object[] topRow = rows.stream()
                .max(Comparator.comparingLong(row -> ((Number) row[1]).longValue()))
                .orElse(null);

        if (topRow == null) {
            return null;
        }

        Long catId = (Long) topRow[0];
        long count = ((Number) topRow[1]).longValue();
        return categoryRepository.findById(catId)
                .map(cat -> new TopCategoryDto(cat.getId(), cat.getName(), count))
                .orElse(null);
    }

    /**
     * DATE_TRUNC 결과 타입 정규화 (Timestamp / LocalDateTime 모두 처리)
     */
    private LocalDateTime toLocalDateTime(Object raw) {
        if (raw instanceof LocalDateTime ldt) {
            return ldt;
        }
        if (raw instanceof Timestamp ts) {
            return ts.toLocalDateTime();
        }
        if (raw instanceof LocalDate ld) {
            return ld.atStartOfDay();
        }
        throw new IllegalArgumentException("DATE_TRUNC 결과를 변환할 수 없습니다: " + raw.getClass());
    }
}
