package com.tulip.tenant.api;

import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.common.tenant.annotation.RequiresTenant;
import com.tulip.tenant.api.dto.LibraryDtos;
import com.tulip.tenant.application.LibraryBranchService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 분관 단건 컨트롤러 ({@code /branches/{id}}).
 *
 * <p>분관 목록·생성은 {@code /libraries/{libId}/branches} 에 위치하고,
 * 단건 패치/삭제는 식별자가 글로벌 유일하므로 별도 root 로 분리한다.</p>
 */
@RestController
@RequestMapping("/api/v1/branches")
@RequiresTenant
@PreAuthorize("hasAnyRole('TENANT_ADMIN','LIB_ADMIN','SYS_ADMIN')")
public class BranchController {

    private final LibraryBranchService branchService;

    public BranchController(LibraryBranchService branchService) {
        this.branchService = branchService;
    }

    @PatchMapping("/{id}")
    public ApiResponse<LibraryDtos.BranchResponse> update(
            @PathVariable Long id,
            @Valid @RequestBody LibraryDtos.BranchUpdateRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        return ApiResponse.success(branchService.update(id, req, parseActor(principal)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable Long id,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        branchService.delete(id, parseActor(principal));
        return ResponseEntity.noContent().build();
    }

    private static Long parseActor(TulipUserPrincipal principal) {
        if (principal == null || principal.userId() == null) return null;
        try { return Long.parseLong(principal.userId()); } catch (NumberFormatException e) { return null; }
    }
}
