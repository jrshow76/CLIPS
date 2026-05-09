package com.footprint.place.dto;

import com.footprint.category.dto.CategoryResponse;
import com.footprint.place.entity.Place;
import com.footprint.place.entity.PlacePhoto;
import com.footprint.place.entity.PlaceTag;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Comparator;
import java.util.List;

public record PlaceSummaryResponse(
        Long id,
        String name,
        String address,
        BigDecimal latitude,
        BigDecimal longitude,
        LocalDate visitedAt,
        Short rating,
        String thumbnailUrl,
        List<CategoryResponse> categories,
        List<String> tags,
        OffsetDateTime createdAt
) {
    public static PlaceSummaryResponse from(Place place, List<CategoryResponse> categories) {
        String thumbnailUrl = place.getPhotos().stream()
                .filter(p -> p.getSortOrder() != null)
                .min(Comparator.comparing(PlacePhoto::getSortOrder))
                .map(p -> p.getThumbnailUrl() != null ? p.getThumbnailUrl() : p.getFileUrl())
                .orElse(null);

        List<String> tags = place.getTags().stream()
                .map(PlaceTag::getTag)
                .toList();

        return new PlaceSummaryResponse(
                place.getId(),
                place.getName(),
                place.getAddress(),
                place.getLatitude(),
                place.getLongitude(),
                place.getVisitedAt(),
                place.getRating(),
                thumbnailUrl,
                categories,
                tags,
                place.getCreatedAt()
        );
    }
}
