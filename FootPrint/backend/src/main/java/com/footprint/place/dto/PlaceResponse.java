package com.footprint.place.dto;

import com.footprint.category.dto.CategoryResponse;
import com.footprint.place.entity.Place;
import com.footprint.place.entity.PlaceTag;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;

public record PlaceResponse(
        Long id,
        String name,
        String address,
        BigDecimal latitude,
        BigDecimal longitude,
        LocalDate visitedAt,
        Short rating,
        String memo,
        List<PhotoResponse> photos,
        List<CategoryResponse> categories,
        List<String> tags,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {
    public static PlaceResponse from(Place place, List<CategoryResponse> categories) {
        List<PhotoResponse> photos = place.getPhotos().stream()
                .map(PhotoResponse::from)
                .toList();

        List<String> tags = place.getTags().stream()
                .map(PlaceTag::getTag)
                .toList();

        return new PlaceResponse(
                place.getId(),
                place.getName(),
                place.getAddress(),
                place.getLatitude(),
                place.getLongitude(),
                place.getVisitedAt(),
                place.getRating(),
                place.getMemo(),
                photos,
                categories,
                tags,
                place.getCreatedAt(),
                place.getUpdatedAt()
        );
    }
}
