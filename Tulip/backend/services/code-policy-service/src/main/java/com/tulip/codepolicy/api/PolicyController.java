package com.tulip.codepolicy.api;

import com.tulip.codepolicy.application.PolicyService;
import com.tulip.codepolicy.dto.PolicyDtos;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.principal.TulipUserPrincipal;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;

/**
 * 정책 REST 컨트롤러.
 *
 * <p>모든 정책 변경은 TENANT_ADMIN 이상. 정책 평가({@code /effective}) 는 사서·소비 서비스가
 * 동기 호출하므로 인증된 모든 사용자가 호출 가능하다.</p>
 */
@RestController
@RequestMapping("/api/v1/policies")
@Tag(name = "policies", description = "정책 및 정책 할당 관리")
public class PolicyController {

    private final PolicyService policyService;

    public PolicyController(PolicyService policyService) {
        this.policyService = policyService;
    }

    @GetMapping
    @PreAuthorize("isAuthenticated()")
    @Operation(summary = "정책 목록")
    public ApiResponse<List<PolicyDtos.PolicyResponse>> list(
            @RequestParam(required = false) String policyCode,
            @RequestParam(required = false) Boolean active) {
        return ApiResponse.success(policyService.list(policyCode, active));
    }

    @GetMapping("/{id}")
    @PreAuthorize("isAuthenticated()")
    @Operation(summary = "정책 단건 조회")
    public ApiResponse<PolicyDtos.PolicyResponse> get(@PathVariable Long id) {
        return ApiResponse.success(policyService.get(id));
    }

    @PostMapping
    @PreAuthorize("hasAnyRole('TENANT_ADMIN','SYS_ADMIN')")
    @Operation(summary = "정책 신규 등록")
    public ResponseEntity<ApiResponse<PolicyDtos.PolicyResponse>> create(
            @Valid @RequestBody PolicyDtos.CreatePolicyRequest req,
            Authentication auth) {
        Long tenantId = tenantIdOf(auth);
        PolicyDtos.PolicyResponse created = policyService.create(tenantId, req);
        return ResponseEntity.created(URI.create("/api/v1/policies/" + created.id()))
                .body(ApiResponse.success(created));
    }

    @PatchMapping("/{id}")
    @PreAuthorize("hasAnyRole('TENANT_ADMIN','SYS_ADMIN')")
    @Operation(summary = "정책 수정")
    public ApiResponse<PolicyDtos.PolicyResponse> update(
            @PathVariable Long id,
            @Valid @RequestBody PolicyDtos.UpdatePolicyRequest req) {
        return ApiResponse.success(policyService.update(id, req));
    }

    @PutMapping("/{id}/assignments")
    @PreAuthorize("hasAnyRole('TENANT_ADMIN','SYS_ADMIN')")
    @Operation(summary = "정책 할당 (라이브러리·회원유형·자료유형)")
    public ApiResponse<PolicyDtos.PolicyResponse> assign(
            @PathVariable Long id,
            @Valid @RequestBody PolicyDtos.AssignmentsRequest req,
            Authentication auth) {
        Long tenantId = tenantIdOf(auth);
        return ApiResponse.success(policyService.assign(id, tenantId, req));
    }

    @GetMapping("/effective")
    @PreAuthorize("isAuthenticated()")
    @Operation(summary = "효력 정책 평가",
            description = "targetType/targetId/policyCode 조합으로 적용될 정책을 결정한다.")
    public ApiResponse<PolicyDtos.EffectivePolicyResponse> effective(
            @RequestParam String targetType,
            @RequestParam String targetId,
            @RequestParam String policyCode) {
        return ApiResponse.success(policyService.evaluate(targetType, targetId, policyCode));
    }

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
