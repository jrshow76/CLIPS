package com.footprint.place.controller;

import com.footprint.common.response.ApiResponse;
import com.footprint.place.dto.PlaceRequest;
import com.footprint.place.dto.PlaceResponse;
import com.footprint.place.dto.PlaceSummaryResponse;
import com.footprint.place.service.PlaceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/places")
@RequiredArgsConstructor
public class PlaceController {

    private final PlaceService placeService;

    @GetMapping
    public ApiResponse<Page<PlaceSummaryResponse>> getPlaces(
            @AuthenticationPrincipal UUID userId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) List<Long> categoryIds,
            @RequestParam(required = false) Integer ratingMin,
            @PageableDefault(size = 20) Pageable pageable) {
        return ApiResponse.ok(placeService.getPlaces(userId, keyword, categoryIds, ratingMin, pageable));
    }

    @GetMapping("/{id}")
    public ApiResponse<PlaceResponse> getPlace(
            @AuthenticationPrincipal UUID userId,
            @PathVariable Long id) {
        return ApiResponse.ok(placeService.getPlace(userId, id));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<PlaceResponse> createPlace(
            @AuthenticationPrincipal UUID userId,
            @Valid @RequestBody PlaceRequest request) {
        return ApiResponse.ok(placeService.createPlace(userId, request));
    }

    @PutMapping("/{id}")
    public ApiResponse<PlaceResponse> updatePlace(
            @AuthenticationPrincipal UUID userId,
            @PathVariable Long id,
            @Valid @RequestBody PlaceRequest request) {
        return ApiResponse.ok(placeService.updatePlace(userId, id, request));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public ApiResponse<Void> deletePlace(
            @AuthenticationPrincipal UUID userId,
            @PathVariable Long id) {
        placeService.deletePlace(userId, id);
        return ApiResponse.ok();
    }

    @GetMapping("/map")
    public ApiResponse<List<PlaceSummaryResponse>> getPlacesInViewport(
            @AuthenticationPrincipal UUID userId,
            @RequestParam BigDecimal swLat, @RequestParam BigDecimal swLng,
            @RequestParam BigDecimal neLat, @RequestParam BigDecimal neLng) {
        return ApiResponse.ok(placeService.getPlacesInViewport(userId, swLat, swLng, neLat, neLng));
    }
}
