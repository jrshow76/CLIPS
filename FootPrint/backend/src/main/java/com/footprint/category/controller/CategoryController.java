package com.footprint.category.controller;

import com.footprint.category.dto.CategoryRequest;
import com.footprint.category.dto.CategoryResponse;
import com.footprint.category.service.CategoryService;
import com.footprint.common.response.ApiResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/categories")
@RequiredArgsConstructor
public class CategoryController {

    private final CategoryService categoryService;

    @GetMapping
    public ApiResponse<List<CategoryResponse>> getCategories(
            @AuthenticationPrincipal UUID userId) {
        return ApiResponse.ok(categoryService.getCategories(userId));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<CategoryResponse> createCategory(
            @AuthenticationPrincipal UUID userId,
            @Valid @RequestBody CategoryRequest request) {
        return ApiResponse.ok(categoryService.createCategory(userId, request));
    }

    @PutMapping("/{id}")
    public ApiResponse<CategoryResponse> updateCategory(
            @AuthenticationPrincipal UUID userId,
            @PathVariable Long id,
            @Valid @RequestBody CategoryRequest request) {
        return ApiResponse.ok(categoryService.updateCategory(userId, id, request));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public ApiResponse<Void> deleteCategory(
            @AuthenticationPrincipal UUID userId,
            @PathVariable Long id) {
        categoryService.deleteCategory(userId, id);
        return ApiResponse.ok();
    }
}
