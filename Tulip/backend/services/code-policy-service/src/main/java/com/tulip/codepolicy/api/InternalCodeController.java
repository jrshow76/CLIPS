package com.tulip.codepolicy.api;

import com.tulip.codepolicy.application.CodeService;
import com.tulip.codepolicy.dto.CodeDtos;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.common.security.principal.TulipUserPrincipal;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 내부 서비스 간 호출 전용 컨트롤러 ({@code /internal/codes/cache/**}).
 *
 * <p>가장 자주 사용되는 코드 그룹은 Redis 캐시 응답을 그대로 반환하여 P50 응답을 단축한다.</p>
 */
@RestController
@RequestMapping("/internal/codes")
@Tag(name = "internal-codes", description = "내부 호출 — 캐시 우선 응답")
public class InternalCodeController {

    private final CodeService codeService;

    public InternalCodeController(CodeService codeService) {
        this.codeService = codeService;
    }

    @GetMapping("/cache/groups/{groupCode}")
    @PreAuthorize("isAuthenticated()")
    @Operation(summary = "캐시 우선 코드 값 조회")
    public ApiResponse<List<CodeDtos.CodeItemResponse>> cached(
            @PathVariable String groupCode,
            Authentication auth) {
        Long tenantId = tenantIdOf(auth);
        return ApiResponse.success(codeService.getCached(groupCode, tenantId));
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
