package com.footprint.place.repository;

import com.footprint.auth.entity.User;
import com.footprint.place.entity.Place;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface PlaceRepository extends JpaRepository<Place, Long> {

    /**
     * 사용자 장소 목록 (삭제되지 않은 것, 페이징)
     */
    Page<Place> findByUserAndDeletedAtIsNull(User user, Pageable pageable);

    /**
     * 단건 조회 — 삭제되지 않은 장소만
     */
    Optional<Place> findByIdAndDeletedAtIsNull(Long id);

    /**
     * 키워드(장소명/주소/메모/태그) + 카테고리 필터 + 최소평점 복합 검색
     * categoryIds 가 null 또는 빈 목록이면 필터 미적용,
     * ratingMin 이 null 이면 평점 필터 미적용
     */
    @Query("""
            SELECT DISTINCT p FROM Place p
            LEFT JOIN p.tags t
            LEFT JOIN p.placeCategories pc
            WHERE p.user.id = :userId
              AND p.deletedAt IS NULL
              AND (:keyword IS NULL OR
                   p.name LIKE %:keyword% OR
                   p.address LIKE %:keyword% OR
                   p.memo LIKE %:keyword% OR
                   t.tag LIKE %:keyword%)
              AND (:#{#categoryIds == null || #categoryIds.isEmpty()} = true
                   OR pc.category.id IN :categoryIds)
              AND (:ratingMin IS NULL OR p.rating >= :ratingMin)
            """)
    Page<Place> searchPlaces(
            @Param("userId") UUID userId,
            @Param("keyword") String keyword,
            @Param("categoryIds") List<Long> categoryIds,
            @Param("ratingMin") Integer ratingMin,
            Pageable pageable
    );

    /**
     * 지도 뷰포트 내 장소 조회 (마커 표시용)
     */
    @Query("""
            SELECT p FROM Place p
            WHERE p.user.id = :userId
              AND p.deletedAt IS NULL
              AND p.latitude  BETWEEN :swLat AND :neLat
              AND p.longitude BETWEEN :swLng AND :neLng
            """)
    List<Place> findInViewport(
            @Param("userId") UUID userId,
            @Param("swLat") BigDecimal swLat,
            @Param("swLng") BigDecimal swLng,
            @Param("neLat") BigDecimal neLat,
            @Param("neLng") BigDecimal neLng
    );

    /**
     * 월별 방문 수 집계 (통계용)
     * Object[0] = DATE_TRUNC('month', visitedAt), Object[1] = COUNT
     */
    @Query("""
            SELECT FUNCTION('DATE_TRUNC', 'month', p.visitedAt), COUNT(p)
            FROM Place p
            WHERE p.user.id = :userId
              AND p.deletedAt IS NULL
            GROUP BY FUNCTION('DATE_TRUNC', 'month', p.visitedAt)
            ORDER BY 1 DESC
            """)
    List<Object[]> countByMonth(@Param("userId") UUID userId);

    /**
     * 이번 달 장소 수 (통계 요약용)
     */
    @Query("""
            SELECT COUNT(p) FROM Place p
            WHERE p.user.id = :userId
              AND p.deletedAt IS NULL
              AND FUNCTION('DATE_TRUNC', 'month', p.visitedAt) =
                  FUNCTION('DATE_TRUNC', 'month', CURRENT_DATE)
            """)
    long countThisMonth(@Param("userId") UUID userId);

    /**
     * 전체 장소 수 (삭제 제외)
     * Place.user.id 경로 탐색 — Spring Data JPA 파생 쿼리에서 user_Id 접두어로 해석
     */
    long countByUser_IdAndDeletedAtIsNull(UUID userId);

    /**
     * 카테고리를 사용 중인 장소 수 (카테고리 삭제 가능 여부 확인용)
     * 호출부에서 > 0 비교를 수행한다.
     */
    @Query("""
            SELECT COUNT(p) FROM Place p
            JOIN p.placeCategories pc
            WHERE p.user.id = :userId
              AND p.deletedAt IS NULL
              AND pc.category.id = :categoryId
            """)
    long countByUserIdAndCategoryId(
            @Param("userId") UUID userId,
            @Param("categoryId") Long categoryId
    );

    /**
     * 평균 평점 (통계 요약용)
     */
    @Query("""
            SELECT AVG(CAST(p.rating AS Double))
            FROM Place p
            WHERE p.user.id = :userId
              AND p.deletedAt IS NULL
              AND p.rating IS NOT NULL
            """)
    Double avgRating(@Param("userId") UUID userId);
}
