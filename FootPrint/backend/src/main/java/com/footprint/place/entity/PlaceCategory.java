package com.footprint.place.entity;

import com.footprint.category.entity.Category;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "place_category")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class PlaceCategory {

    @EmbeddedId
    private PlaceCategoryId id;

    @ManyToOne(fetch = FetchType.LAZY)
    @MapsId("placeId")
    @JoinColumn(name = "place_id", nullable = false)
    private Place place;

    @ManyToOne(fetch = FetchType.LAZY)
    @MapsId("categoryId")
    @JoinColumn(name = "category_id", nullable = false)
    private Category category;

    public static PlaceCategory of(Place place, Category category) {
        return PlaceCategory.builder()
                .id(new PlaceCategoryId(place.getId(), category.getId()))
                .place(place)
                .category(category)
                .build();
    }
}
