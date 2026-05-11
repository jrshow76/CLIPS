package com.tulip.codepolicy.api;

import com.tulip.codepolicy.application.CodeService;
import com.tulip.codepolicy.dto.CodeDtos;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.principal.TulipUserPrincipal;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

/**
 * 코드(그룹/값) REST 컨트롤러.
 *
 * <p>{@code /api/v1/codes/groups/**} 는 인증된 사용자라면 조회 가능.
 * 변경(POST/PATCH/DELETE) 은 TENANT_ADMIN 이상, 글로벌 코드는 SYS_ADMIN.</p>
 */
@RestController
@RequestMapping("/api/v1/codes")
@Tag(name = "codes", description = "코드 그룹·코드 관리")
public class CodeController {

    private final CodeService codeService;

    public CodeController(CodeService codeService) {
        this.codeService = codeService;
    }

    @GetMapping("/groups")
    @PreAuthorize("isAuthenticated()")
    @Operation(summary = "코드 그룹 목록 (글로벌 + 테넌트)")
    public ApiResponse<List<CodeDtos.CodeGroupResponse>> listGroups(Authentication auth) {
        Long tenantId = tenantIdOf(auth);
        return ApiResponse.success(codeService.listGroups(tenantId));
    }

    @GetMapping("/groups/{groupCode}/items")
    @PreAuthorize("isAuthenticated()")
    @Operation(summary = "코드 값 목록 (계층 포함)")
    public ApiResponse<List<CodeDtos.CodeItemResponse>> listItems(
            @PathVariable String groupCode,
            Authentication auth) {
        Long tenantId = tenantIdOf(auth);
        return ApiResponse.success(codeService.listItems(groupCode, tenantId));
    }

    @GetMapping("/groups/{groupCode}/items/{code}")
    @PreAuthorize("isAuthenticated()")
    @Operation(summary = "코드 단건 조회")
    public ApiResponse<CodeDtos.CodeItemResponse> get(
            @PathVariable String groupCode,
            @PathVariable String code,
            Authentication auth) {
        return ApiResponse.success(codeService.getItem(groupCode, code, tenantIdOf(auth)));
    }

    @PostMapping("/groups/{groupCode}/items")
    @PreAuthorize("hasAnyRole('TENANT_ADMIN','SYS_ADMIN')")
    @Operation(summary = "코드 추가 (테넌트 한정)")
    public ResponseEntity<ApiResponse<CodeDtos.CodeItemResponse>> create(
            @PathVariable String groupCode,
            @Valid @RequestBody CodeDtos.CreateCodeItemRequest req,
            Authentication auth) {
        Long tenantId = tenantIdOf(auth);
        CodeDtos.CodeItemResponse created = codeService.create(groupCode, tenantId, req);
        return ResponseEntity.created(URI.create("/api/v1/codes/items/" + created.id()))
                .body(ApiResponse.success(created));
    }

    @PatchMapping("/items/{id}")
    @PreAuthorize("hasAnyRole('TENANT_ADMIN','SYS_ADMIN')")
    @Operation(summary = "코드 수정")
    public ApiResponse<CodeDtos.CodeItemResponse> update(
            @PathVariable Long id,
            @Valid @RequestBody CodeDtos.UpdateCodeItemRequest req,
            Authentication auth) {
        return ApiResponse.success(codeService.update(id, tenantIdOf(auth), req));
    }

    @DeleteMapping("/items/{id}")
    @PreAuthorize("hasAnyRole('TENANT_ADMIN','SYS_ADMIN')")
    @Operation(summary = "코드 삭제")
    public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) {
        codeService.delete(id);
        return ResponseEntity.noContent().build();
    }

    /* ============================== Helpers ============================== */

    private static Long tenantIdOf(Authentication auth) {
        if (auth == null || !(auth.getPrincipal() instanceof TulipUserPrincipal p)) {
            return null;
        }
        try {
            return p.tenantId() == null ? null : Long.parseLong(p.tenantId());
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
