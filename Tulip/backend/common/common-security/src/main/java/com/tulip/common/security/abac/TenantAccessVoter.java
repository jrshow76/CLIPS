package com.tulip.common.security.abac;

import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;

/**
 * 테넌트 격리(R-06) 검증 ABAC Voter.
 *
 * <p>{@code 05_security_and_auth.md} §3.4 — JWT 토큰의 tenantId 와 현재 요청 컨텍스트의
 * tenantId(헤더 또는 자원 소유 테넌트)가 일치하는지 확인한다.</p>
 *
 * <p>사용 예 (SpEL — {@code @PreAuthorize}):
 * <pre>
 * &#64;PreAuthorize("@tenantAccessVoter.canAccess(principal, #resourceTenantId)")
 * public ResponseDto getOne(&#64;PathVariable String resourceTenantId) { ... }
 * </pre>
 *
 * <p>PLATFORM_ADMIN 역할 보유자는 임의 테넌트 전환이 허용된다(헌장 §4.3).
 * 단 모든 전환은 별도 감사로그에 기록되어야 한다(IAM 책임).</p>
 */
public class TenantAccessVoter {

    /**
     * 사용자 토큰의 tenantId 와 자원 tenantId 일치 여부를 검사한다.
     *
     * @param principal       JWT 에서 추출된 사용자
     * @param resourceTenant  접근 대상 자원의 tenantId
     * @return 접근 허용이면 {@code true}
     */
    public boolean canAccess(TulipUserPrincipal principal, String resourceTenant) {
        if (principal == null || resourceTenant == null) {
            return false;
        }
        // 플랫폼 관리자: 임의 테넌트 허용
        if (principal.hasRole("PLATFORM_ADMIN") || principal.hasRole("SYS_ADMIN")) {
            return true;
        }
        return resourceTenant.equals(principal.tenantId());
    }

    /** TenantContext(헤더 전파 결과) 와 토큰을 비교한다. */
    public boolean canAccessCurrent(TulipUserPrincipal principal) {
        TenantContext ctx = TenantContextHolder.get();
        if (ctx == null || ctx.tenantId() == null) {
            // 컨텍스트 미설정 → 토큰의 tenantId 가 존재하면 통과(서비스 내부 호출 가정)
            return principal != null && principal.tenantId() != null;
        }
        return canAccess(principal, ctx.tenantId());
    }

    /** 특정 branch(library) 접근 가능 여부. */
    public boolean canAccessBranch(TulipUserPrincipal principal, String branchId) {
        if (principal == null || branchId == null) {
            return false;
        }
        if (principal.hasRole("PLATFORM_ADMIN") || principal.hasRole("SYS_ADMIN")
                || principal.hasRole("TENANT_ADMIN")) {
            return true;
        }
        return principal.libraryIds() != null && principal.libraryIds().contains(branchId);
    }
}
