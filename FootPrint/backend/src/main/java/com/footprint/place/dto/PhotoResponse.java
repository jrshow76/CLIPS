package com.footprint.place.dto;

import com.footprint.place.entity.PlacePhoto;

public record PhotoResponse(
        Long id,
        String fileUrl,
        String thumbnailUrl,
        String originalName,
        Short sortOrder
) {
    public static PhotoResponse from(PlacePhoto photo) {
        return new PhotoResponse(
                photo.getId(),
                photo.getFileUrl(),
                photo.getThumbnailUrl(),
                photo.getOriginalName(),
                photo.getSortOrder()
        );
    }
}
