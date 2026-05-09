package com.footprint.category.repository;

import com.footprint.category.entity.Category;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface CategoryRepository extends JpaRepository<Category, Long> {

    /**
     * 사용자 전용 카테고리 + 시스템 기본 카테고리를 sortOrder 기준으로 조회
     */
    List<Category> findByUserIdOrIsDefaultTrueOrderBySortOrder(UUID userId);

    /**
     * 동일 사용자 내 카테고리명 중복 여부 확인
     */
    boolean existsByUserIdAndName(UUID userId, String name);

    /**
     * 사용자가 생성한 비기본 카테고리 수 (20개 제한용)
     */
    long countByUserIdAndIsDefaultFalse(UUID userId);

    /**
     * 특정 카테고리 ID 목록에서 해당 사용자 소유(또는 기본)인 것만 조회 — 장소 저장 시 유효성 검증용
     */
    @Query("SELECT c FROM Category c WHERE c.id IN :ids AND (c.userId = :userId OR c.isDefault = true)")
    List<Category> findAllByIdInAndAccessible(@Param("ids") List<Long> ids, @Param("userId") UUID userId);

    /**
     * 카테고리별 장소 수 집계 — 통계용
     */
    @Query("SELECT pc.category.id, COUNT(pc) FROM PlaceCategory pc " +
           "WHERE pc.place.user.id = :userId AND pc.place.deletedAt IS NULL " +
           "GROUP BY pc.category.id")
    List<Object[]> countPlacesByCategory(@Param("userId") UUID userId);
}
