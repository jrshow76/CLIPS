package com.footprint.place.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;
import lombok.*;

import java.io.Serializable;

@Embeddable
@Getter
@NoArgsConstructor
@AllArgsConstructor
@EqualsAndHashCode
public class PlaceCategoryId implements Serializable {

    @Column(name = "place_id")
    private Long placeId;

    @Column(name = "category_id")
    private Long categoryId;
}
