package com.shelfy.item.controller;

import com.shelfy.common.response.ApiResponse;
import com.shelfy.common.response.PageResponse;
import com.shelfy.item.dto.request.CreateItemRequest;
import com.shelfy.item.dto.request.ItemSearchCondition;
import com.shelfy.item.dto.request.UpdateItemRequest;
import com.shelfy.item.dto.response.ItemDetailResponse;
import com.shelfy.item.dto.response.ItemSummaryResponse;
import com.shelfy.item.entity.Item;
import com.shelfy.item.service.ItemService;
import com.shelfy.security.CustomUserDetails;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 상품 API 컨트롤러
 * <p>
 * Base URL: /api/v1/items
 */
@RestController
@RequestMapping("/api/v1/items")
@RequiredArgsConstructor
public class ItemController {

    private final ItemService itemService;

    /**
     * POST /api/v1/items - 상품 등록
     * 이메일 인증 완료한 로그인 사용자만 가능
     */
    @PostMapping
    public ResponseEntity<ApiResponse<Map<String, Long>>> createItem(
            @RequestBody @Valid CreateItemRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        Long itemId = itemService.createItem(
                request, userDetails.getUserId(), userDetails.isEmailVerified());
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success(Map.of("itemId", itemId)));
    }

    /**
     * GET /api/v1/items - 상품 목록 탐색 (피드, 공개)
     */
    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ItemSummaryResponse>>> getItems(
            @ModelAttribute ItemSearchCondition condition) {
        PageResponse<ItemSummaryResponse> response = itemService.getPublishedItems(condition);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * GET /api/v1/items/search - 상품 검색 (공개)
     */
    @GetMapping("/search")
    public ResponseEntity<ApiResponse<PageResponse<ItemSummaryResponse>>> searchItems(
            @ModelAttribute ItemSearchCondition condition) {
        PageResponse<ItemSummaryResponse> response = itemService.searchItems(condition);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * GET /api/v1/items/my - 내 상품 목록 조회 (셀러)
     */
    @GetMapping("/my")
    public ResponseEntity<ApiResponse<PageResponse<ItemSummaryResponse>>> getMyItems(
            @ModelAttribute ItemSearchCondition condition,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        PageResponse<ItemSummaryResponse> response = itemService.getMyItems(condition, userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * GET /api/v1/items/{itemId} - 상품 상세 조회 (공개, DRAFT는 본인만)
     */
    @GetMapping("/{itemId}")
    public ResponseEntity<ApiResponse<ItemDetailResponse>> getItem(
            @PathVariable Long itemId,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        Long viewerId = (userDetails != null) ? userDetails.getUserId() : null;
        ItemDetailResponse response = itemService.getItemDetail(itemId, viewerId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * PUT /api/v1/items/{itemId} - 상품 수정 (소유자만)
     */
    @PutMapping("/{itemId}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> updateItem(
            @PathVariable Long itemId,
            @RequestBody @Valid UpdateItemRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        Map<String, Object> result = itemService.updateItem(itemId, request, userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    /**
     * DELETE /api/v1/items/{itemId} - 상품 삭제 (소유자만, 소프트 삭제)
     */
    @DeleteMapping("/{itemId}")
    public ResponseEntity<Void> deleteItem(
            @PathVariable Long itemId,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        itemService.deleteItem(itemId, userDetails.getUserId());
        return ResponseEntity.noContent().build();
    }

    /**
     * PATCH /api/v1/items/{itemId}/status - 상품 상태 변경
     */
    @PatchMapping("/{itemId}/status")
    public ResponseEntity<ApiResponse<Map<String, Object>>> updateItemStatus(
            @PathVariable Long itemId,
            @RequestBody Map<String, String> body,
            @AuthenticationPrincipal CustomUserDetails userDetails) {
        Item.ItemStatus status = Item.ItemStatus.valueOf(body.get("status"));
        Map<String, Object> result = itemService.updateItemStatus(itemId, status, userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(result));
    }
}
