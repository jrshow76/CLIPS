package com.tulip.tenant.api;

import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.tenant.api.dto.TenantDtos;
import com.tulip.tenant.application.TenantService;
import com.tulip.tenant.security.SystemAdmin;
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

/**
 * 테넌트(시스템 관리자 전용) REST 컨트롤러.
 *
 * <p>SYS_ADMIN 역할만 호출 가능하며 RLS 우회 모드(X-Sys-Bypass: true)로 동작한다.</p>
 */
@RestController
@RequestMapping("/api/v1/tenants")
@PreAuthorize("hasRole('SYS_ADMIN')")
public class TenantController {

    private final TenantService tenantService;

    public TenantController(TenantService tenantService) {
        this.tenantService = tenantService;
    }

    @PostMapping
    @SystemAdmin
    public ResponseEntity<ApiResponse<TenantDtos.Response>> create(
            @Valid @RequestBody TenantDtos.CreateRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        TenantDtos.Response created = tenantService.create(req, parseActor(principal));
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.success(created));
    }

    @GetMapping
    @SystemAdmin
    public ApiResponse<java.util.List<TenantDtos.Response>> search(
            @RequestParam(required = false) String code,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int offset,
            @RequestParam(defaultValue = "20") int limit
    ) {
        TenantService.SearchResult r = tenantService.search(
                new TenantDtos.SearchCondition(code, name, status, offset, limit));
        return ApiResponse.success(r.items(), r.meta());
    }

    @GetMapping("/{id}")
    @SystemAdmin
    public ApiResponse<TenantDtos.Response> getOne(@PathVariable Long id) {
        return ApiResponse.success(tenantService.getById(id));
    }

    @PatchMapping("/{id}")
    @SystemAdmin
    public ApiResponse<TenantDtos.Response> update(
            @PathVariable Long id,
            @Valid @RequestBody TenantDtos.UpdateRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        return ApiResponse.success(tenantService.update(id, req, parseActor(principal)));
    }

    @DeleteMapping("/{id}")
    @SystemAdmin
    public ResponseEntity<Void> close(
            @PathVariable Long id,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        tenantService.close(id, parseActor(principal));
        return ResponseEntity.noContent().build();
    }

    private static Long parseActor(TulipUserPrincipal principal) {
        if (principal == null || principal.userId() == null) return null;
        try { return Long.parseLong(principal.userId()); } catch (NumberFormatException e) { return null; }
    }
}
