package com.tulip.tenant.api;

import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.common.tenant.annotation.RequiresTenant;
import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;
import com.tulip.tenant.api.dto.LibraryDtos;
import com.tulip.tenant.application.LibraryBranchService;
import com.tulip.tenant.application.LibraryService;
import com.tulip.tenant.error.TenantErrorCode;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 라이브러리(Library) REST 컨트롤러.
 *
 * <p>tenant 컨텍스트 자동 적용 — RLS 정책으로 다른 테넌트 라이브러리는 보이지 않는다.</p>
 */
@RestController
@RequestMapping("/api/v1/libraries")
@RequiresTenant(allowPlatformAdmin = true)
@PreAuthorize("hasAnyRole('TENANT_ADMIN','LIB_ADMIN','SYS_ADMIN')")
public class LibraryController {

    private final LibraryService libraryService;
    private final LibraryBranchService branchService;

    public LibraryController(LibraryService libraryService, LibraryBranchService branchService) {
        this.libraryService = libraryService;
        this.branchService = branchService;
    }

    @PostMapping
    public ResponseEntity<ApiResponse<LibraryDtos.Response>> create(
            @Valid @RequestBody LibraryDtos.CreateRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        LibraryDtos.Response r = libraryService.create(req, requireTenantId(), parseActor(principal));
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(r));
    }

    @GetMapping
    public ApiResponse<List<LibraryDtos.Response>> search(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int offset,
            @RequestParam(defaultValue = "20") int limit
    ) {
        LibraryService.SearchResult r = libraryService.search(
                new LibraryDtos.SearchCondition(name, status, offset, limit));
        return ApiResponse.success(r.items(), r.meta());
    }

    @GetMapping("/{id}")
    public ApiResponse<LibraryDtos.Response> getOne(@PathVariable Long id) {
        return ApiResponse.success(libraryService.getById(id));
    }

    @PatchMapping("/{id}")
    public ApiResponse<LibraryDtos.Response> update(
            @PathVariable Long id,
            @Valid @RequestBody LibraryDtos.UpdateRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        return ApiResponse.success(libraryService.update(id, req, parseActor(principal)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(
            @PathVariable Long id,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        libraryService.delete(id, parseActor(principal));
        return ResponseEntity.noContent().build();
    }

    // ---------- 분관 (nested) ----------

    @PostMapping("/{libId}/branches")
    public ResponseEntity<ApiResponse<LibraryDtos.BranchResponse>> createBranch(
            @PathVariable Long libId,
            @Valid @RequestBody LibraryDtos.BranchCreateRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        LibraryDtos.BranchResponse r = branchService.create(libId, req, parseActor(principal));
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(r));
    }

    @GetMapping("/{libId}/branches")
    public ApiResponse<List<LibraryDtos.BranchResponse>> listBranches(@PathVariable Long libId) {
        return ApiResponse.success(branchService.listByLibrary(libId));
    }

    private Long requireTenantId() {
        TenantContext ctx = TenantContextHolder.get();
        if (ctx == null || ctx.tenantId() == null) {
            throw new NotFoundException(TenantErrorCode.TENANT_NOT_FOUND);
        }
        try { return Long.parseLong(ctx.tenantId()); }
        catch (NumberFormatException e) { throw new NotFoundException(TenantErrorCode.TENANT_NOT_FOUND); }
    }

    private static Long parseActor(TulipUserPrincipal principal) {
        if (principal == null || principal.userId() == null) return null;
        try { return Long.parseLong(principal.userId()); } catch (NumberFormatException e) { return null; }
    }
}
