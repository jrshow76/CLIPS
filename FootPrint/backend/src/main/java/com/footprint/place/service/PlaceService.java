package com.footprint.place.service;

import com.footprint.auth.entity.User;
import com.footprint.auth.repository.UserRepository;
import com.footprint.category.dto.CategoryResponse;
import com.footprint.category.entity.Category;
import com.footprint.category.repository.CategoryRepository;
import com.footprint.common.exception.CustomException;
import com.footprint.common.exception.ErrorCode;
import com.footprint.place.dto.PlaceRequest;
import com.footprint.place.dto.PlaceResponse;
import com.footprint.place.dto.PlaceSummaryResponse;
import com.footprint.place.entity.Place;
import com.footprint.place.entity.PlaceCategory;
import com.footprint.place.entity.PlaceCategoryId;
import com.footprint.place.entity.PlaceTag;
import com.footprint.place.repository.PlaceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class PlaceService {

    private final PlaceRepository placeRepository;
    private final UserRepository userRepository;
    private final CategoryRepository categoryRepository;

    /**
     * 장소 목록 조회 (키워드 LIKE, 카테고리 필터, 평점 필터, 페이징)
     */
    public Page<PlaceSummaryResponse> getPlaces(UUID userId, String keyword,
                                                 List<Long> categoryIds, Integer ratingMin,
                                                 Pageable pageable) {
        Page<Place> places = placeRepository.searchPlaces(userId, keyword, categoryIds, ratingMin, pageable);
        return places.map(place -> {
            List<CategoryResponse> categories = buildCategoryResponses(place);
            return PlaceSummaryResponse.from(place, categories);
        });
    }

    /**
     * 장소 상세 조회 — 본인 소유 확인
     */
    public PlaceResponse getPlace(UUID userId, Long id) {
        Place place = findOwnedPlace(userId, id);
        List<CategoryResponse> categories = buildCategoryResponses(place);
        return PlaceResponse.from(place, categories);
    }

    /**
     * 장소 등록 — 카테고리 연결, 태그 저장
     */
    @Transactional
    public PlaceResponse createPlace(UUID userId, PlaceRequest request) {
        User user = findUser(userId);
        List<Category> categories = resolveCategories(userId, request.categoryIds());

        Place place = Place.builder()
                .user(user)
                .name(request.name())
                .address(request.address())
                .latitude(request.latitude())
                .longitude(request.longitude())
                .visitedAt(request.visitedAt())
                .memo(request.memo())
                .rating(request.rating())
                .build();

        // 카테고리 연결 (PlaceCategory 는 Place 저장 후 id 확정 시점에 추가)
        Place saved = placeRepository.save(place);

        attachCategories(saved, categories);
        attachTags(saved, request.tags());

        List<CategoryResponse> categoryResponses = categories.stream()
                .map(CategoryResponse::from)
                .toList();
        return PlaceResponse.from(saved, categoryResponses);
    }

    /**
     * 장소 수정 — 소유권 확인, 카테고리/태그 전체 교체
     */
    @Transactional
    public PlaceResponse updatePlace(UUID userId, Long id, PlaceRequest request) {
        Place place = findOwnedPlace(userId, id);
        List<Category> categories = resolveCategories(userId, request.categoryIds());

        place.update(
                request.name(),
                request.address(),
                request.latitude(),
                request.longitude(),
                request.visitedAt(),
                request.memo(),
                request.rating()
        );

        // 카테고리 교체 (기존 전체 삭제 후 재등록)
        place.getPlaceCategories().clear();
        attachCategories(place, categories);

        // 태그 교체
        place.getTags().clear();
        attachTags(place, request.tags());

        List<CategoryResponse> categoryResponses = categories.stream()
                .map(CategoryResponse::from)
                .toList();
        return PlaceResponse.from(place, categoryResponses);
    }

    /**
     * 장소 Soft Delete
     */
    @Transactional
    public void deletePlace(UUID userId, Long id) {
        Place place = findOwnedPlace(userId, id);
        place.delete();
    }

    /**
     * 지도 뷰포트 내 장소 조회
     */
    public List<PlaceSummaryResponse> getPlacesInViewport(UUID userId,
                                                           BigDecimal swLat, BigDecimal swLng,
                                                           BigDecimal neLat, BigDecimal neLng) {
        List<Place> places = placeRepository.findInViewport(userId, swLat, swLng, neLat, neLng);
        return places.stream()
                .map(place -> {
                    List<CategoryResponse> categories = buildCategoryResponses(place);
                    return PlaceSummaryResponse.from(place, categories);
                })
                .toList();
    }

    // -------------------------------------------------------------------------
    // private helpers
    // -------------------------------------------------------------------------

    private Place findOwnedPlace(UUID userId, Long id) {
        Place place = placeRepository.findByIdAndDeletedAtIsNull(id)
                .orElseThrow(() -> new CustomException(ErrorCode.PLACE_NOT_FOUND));

        if (!place.getUser().getId().equals(userId)) {
            throw new CustomException(ErrorCode.FORBIDDEN);
        }
        return place;
    }

    private User findUser(UUID userId) {
        return userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.UNAUTHORIZED));
    }

    /**
     * 요청된 카테고리 ID 목록 검증 후 Category 엔티티 목록 반환
     * 존재하지 않거나 접근 불가한 카테고리가 하나라도 있으면 예외
     */
    private List<Category> resolveCategories(UUID userId, List<Long> categoryIds) {
        List<Category> found = categoryRepository.findAllByIdInAndAccessible(categoryIds, userId);
        if (found.size() != categoryIds.size()) {
            throw new CustomException(ErrorCode.CATEGORY_NOT_FOUND);
        }
        return found;
    }

    private void attachCategories(Place place, List<Category> categories) {
        for (Category category : categories) {
            PlaceCategory pc = PlaceCategory.builder()
                    .id(new PlaceCategoryId(place.getId(), category.getId()))
                    .place(place)
                    .category(category)
                    .build();
            place.getPlaceCategories().add(pc);
        }
    }

    private void attachTags(Place place, List<String> tags) {
        if (tags == null || tags.isEmpty()) {
            return;
        }
        for (String tagValue : tags) {
            PlaceTag tag = PlaceTag.builder()
                    .place(place)
                    .tag(tagValue)
                    .build();
            place.getTags().add(tag);
        }
    }

    private List<CategoryResponse> buildCategoryResponses(Place place) {
        return place.getPlaceCategories().stream()
                .map(pc -> CategoryResponse.from(pc.getCategory()))
                .toList();
    }
}
