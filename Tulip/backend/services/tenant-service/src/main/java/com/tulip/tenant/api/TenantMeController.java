package com.tulip.tenant.api;

import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.common.tenant.annotation.RequiresTenant;
import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;
import com.tulip.tenant.api.dto.TenantDtos;
import com.tulip.tenant.api.dto.TenantSettingDtos;
import com.tulip.tenant.application.TenantService;
import com.tulip.tenant.application.TenantSettingService;
import com.tulip.tenant.error.TenantErrorCode;
import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 현재 테넌트(/me) 컨트롤러.
 *
 * <p>TENANT_ADMIN/SYS_ADMIN 역할 사용자가 자기 테넌트를 조회/수정하고
 * 설정 KV 를 관리한다. JWT 의 {@code tenant_id} 클레임 → {@link TenantContextHolder} 에서 가져온다.</p>
 */
@RestController
@RequestMapping("/api/v1/tenants/me")
@RequiresTenant
@PreAuthorize("hasAnyRole('TENANT_ADMIN','SYS_ADMIN')")
public class TenantMeController {

    private final TenantService tenantService;
    private final TenantSettingService settingService;

    public TenantMeController(TenantService tenantService, TenantSettingService settingService) {
        this.tenantService = tenantService;
        this.settingService = settingService;
    }

    @GetMapping
    public ApiResponse<TenantDtos.Response> getMe() {
        Long tenantId = requireTenantId();
        return ApiResponse.success(tenantService.getById(tenantId));
    }

    @PatchMapping
    public ApiResponse<TenantDtos.Response> updateMe(
            @Valid @RequestBody TenantDtos.UpdateRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        // 본인 테넌트는 status 변경 불가 (시스템 관리자만 가능)
        if (req.status() != null && !principal.hasRole("SYS_ADMIN")) {
            throw new com.tulip.common.core.exception.BusinessException(
                    TenantErrorCode.SYSTEM_ADMIN_REQUIRED);
        }
        return ApiResponse.success(
                tenantService.update(requireTenantId(), req, parseActor(principal)));
    }

    @GetMapping("/settings")
    public ApiResponse<List<TenantSettingDtos.Response>> listSettings() {
        return ApiResponse.success(settingService.listByTenant(requireTenantId()));
    }

    @PutMapping("/settings/{key}")
    public ApiResponse<TenantSettingDtos.Response> upsertSetting(
            @PathVariable String key,
            @Valid @RequestBody TenantSettingDtos.UpsertRequest req,
            @AuthenticationPrincipal TulipUserPrincipal principal
    ) {
        return ApiResponse.success(
                settingService.upsert(requireTenantId(), key, req, parseActor(principal)));
    }

    @GetMapping("/settings/{key}")
    public ApiResponse<TenantSettingDtos.Response> getSetting(@PathVariable String key) {
        return ApiResponse.success(settingService.getByKey(requireTenantId(), key));
    }

    private Long requireTenantId() {
        TenantContext ctx = TenantContextHolder.get();
        if (ctx == null || ctx.tenantId() == null) {
            throw new NotFoundException(TenantErrorCode.TENANT_NOT_FOUND);
        }
        try {
            return Long.parseLong(ctx.tenantId());
        } catch (NumberFormatException e) {
            throw new NotFoundException(TenantErrorCode.TENANT_NOT_FOUND);
        }
    }

    private static Long parseActor(TulipUserPrincipal principal) {
        if (principal == null || principal.userId() == null) return null;
        try { return Long.parseLong(principal.userId()); } catch (NumberFormatException e) { return null; }
    }
}
