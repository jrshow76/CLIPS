package com.footprint.category.service;

import com.footprint.category.dto.CategoryRequest;
import com.footprint.category.dto.CategoryResponse;
import com.footprint.category.entity.Category;
import com.footprint.category.repository.CategoryRepository;
import com.footprint.common.exception.CustomException;
import com.footprint.common.exception.ErrorCode;
import com.footprint.place.repository.PlaceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class CategoryService {

    private static final int CATEGORY_MAX_COUNT = 20;

    private final CategoryRepository categoryRepository;
    private final PlaceRepository placeRepository;

    /**
     * 시스템 기본 카테고리 + 사용자 정의 카테고리 목록 조회
     * 각 카테고리의 장소 수를 함께 반환한다.
     */
    public List<CategoryResponse> getCategories(UUID userId) {
        List<Category> categories =
                categoryRepository.findByUserIdOrIsDefaultTrueOrderBySortOrder(userId);

        // 카테고리별 장소 수 집계 (단일 쿼리)
        Map<Long, Long> placeCountMap = categoryRepository.countPlacesByCategory(userId)
                .stream()
                .collect(Collectors.toMap(
                        row -> (Long) row[0],
                        row -> (Long) row[1]
                ));

        return categories.stream()
                .map(c -> CategoryResponse.from(c, placeCountMap.getOrDefault(c.getId(), 0L)))
                .toList();
    }

    /**
     * 사용자 카테고리 생성 (최대 20개 제한)
     */
    @Transactional
    public CategoryResponse createCategory(UUID userId, CategoryRequest request) {
        if (categoryRepository.countByUserIdAndIsDefaultFalse(userId) >= CATEGORY_MAX_COUNT) {
            throw new CustomException(ErrorCode.CATEGORY_LIMIT);
        }
        if (categoryRepository.existsByUserIdAndName(userId, request.name())) {
            throw new CustomException(ErrorCode.DUPLICATE_CATEGORY_NAME);
        }

        Category category = Category.builder()
                .userId(userId)
                .name(request.name())
                .color(request.color() != null ? request.color() : "#9E9E9E")
                .icon(request.icon())
                .isDefault(false)
                .sortOrder(0)
                .build();

        Category saved = categoryRepository.save(category);
        return CategoryResponse.from(saved, 0L);
    }

    /**
     * 카테고리 수정 — 기본 카테고리는 수정 불가
     */
    @Transactional
    public CategoryResponse updateCategory(UUID userId, Long id, CategoryRequest request) {
        Category category = findAccessibleCategory(userId, id);

        if (category.isDefault()) {
            throw new CustomException(ErrorCode.DEFAULT_CATEGORY_IMMUTABLE);
        }

        // 이름 변경 시 중복 검사 (현재 이름과 다를 때만)
        if (!category.getName().equals(request.name()) &&
            categoryRepository.existsByUserIdAndName(userId, request.name())) {
            throw new CustomException(ErrorCode.DUPLICATE_CATEGORY_NAME);
        }

        category.update(request.name(), request.color(), request.icon());

        Map<Long, Long> countMap = categoryRepository.countPlacesByCategory(userId)
                .stream()
                .collect(Collectors.toMap(row -> (Long) row[0], row -> (Long) row[1]));

        return CategoryResponse.from(category, countMap.getOrDefault(id, 0L));
    }

    /**
     * 카테고리 삭제 — 기본 카테고리 삭제 불가, 사용 중인 카테고리 삭제 불가
     */
    @Transactional
    public void deleteCategory(UUID userId, Long id) {
        Category category = findAccessibleCategory(userId, id);

        if (category.isDefault()) {
            throw new CustomException(ErrorCode.DEFAULT_CATEGORY_IMMUTABLE);
        }
        if (placeRepository.countByUserIdAndCategoryId(userId, id) > 0) {
            throw new CustomException(ErrorCode.CATEGORY_IN_USE);
        }

        categoryRepository.delete(category);
    }

    /**
     * 카테고리 조회 + 접근 권한 확인 (공통)
     * 기본 카테고리이거나 본인 카테고리인 경우에만 접근 허용
     */
    private Category findAccessibleCategory(UUID userId, Long id) {
        Category category = categoryRepository.findById(id)
                .orElseThrow(() -> new CustomException(ErrorCode.CATEGORY_NOT_FOUND));

        if (!category.isDefault() &&
            (category.getUserId() == null || !category.getUserId().equals(userId))) {
            throw new CustomException(ErrorCode.FORBIDDEN);
        }
        return category;
    }
}
