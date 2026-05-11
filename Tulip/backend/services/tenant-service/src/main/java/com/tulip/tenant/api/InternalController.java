package com.tulip.tenant.api;

import com.tulip.common.core.exception.NotFoundException;
import com.tulip.common.core.response.ApiResponse;
import com.tulip.tenant.application.LibraryService;
import com.tulip.tenant.application.TenantService;
import com.tulip.tenant.domain.Library;
import com.tulip.tenant.error.TenantErrorCode;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * 내부 서비스 호출용 read-only 컨트롤러.
 *
 * <p>service-to-service 토큰의 {@code SCOPE_internal} 클레임 보유자만 호출 가능.</p>
 */
@RestController
@RequestMapping("/api/v1/internal")
@PreAuthorize("hasAuthority('SCOPE_internal')")
public class InternalController {

    private final TenantService tenantService;
    private final LibraryService libraryService;

    public InternalController(TenantService tenantService, LibraryService libraryService) {
        this.tenantService = tenantService;
        this.libraryService = libraryService;
    }

    /** 테넌트 존재/활성 여부 — 다른 서비스 게이트. */
    @GetMapping("/tenants/{id}/exists")
    public ApiResponse<Map<String, Object>> tenantExists(@PathVariable Long id) {
        boolean exists = tenantService.existsById(id);
        return ApiResponse.success(Map.of(
                "id", id,
                "exists", exists
        ));
    }

    /**
     * 라이브러리 컨텍스트(라이브러리 + tenantId) 조회.
     *
     * <p>회원/소장 등 다른 서비스가 라이브러리 메타를 빠르게 가져갈 때 사용.
     * Redis 캐시는 호출 측에서 적용하거나, 향후 본 컨트롤러에 {@code @Cacheable} 추가 가능.</p>
     */
    @GetMapping("/libraries/{id}/context")
    public ApiResponse<Map<String, Object>> libraryContext(@PathVariable Long id) {
        try {
            Library lib = libraryService.requireById(id);
            return ApiResponse.success(Map.of(
                    "id", lib.getId(),
                    "publicId", lib.getPublicId(),
                    "tenantId", lib.getTenantId(),
                    "code", lib.getCode(),
                    "name", lib.getName(),
                    "type", lib.getType().name(),
                    "status", lib.getStatus().name()
            ));
        } catch (NotFoundException ex) {
            throw new NotFoundException(TenantErrorCode.LIBRARY_NOT_FOUND);
        }
    }
}
