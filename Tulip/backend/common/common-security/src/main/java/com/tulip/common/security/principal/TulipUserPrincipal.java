package com.tulip.common.security.principal;

import java.io.Serial;
import java.io.Serializable;
import java.util.List;
import java.util.Set;

/**
 * 인증된 사용자 식별 정보 (Spring Security Principal).
 *
 * <p>JWT 의 표준 클레임 {@code sub/tenantId/libraryIds/roles/scopes/memberType} 를 매핑한다.
 * 클레임 정의는 {@code 05_security_and_auth.md} §2.4 를 따른다.</p>
 */
public record TulipUserPrincipal(
        String userId,
        String tenantId,
        List<String> libraryIds,
        String primaryLibraryId,
        Set<String> roles,
        Set<String> scopes,
        String memberType,
        String deviceId,
        String tokenId
) implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    /** 플랫폼 관리자 여부. */
    public boolean isPlatformAdmin() {
        return "PLATFORM_ADMIN".equalsIgnoreCase(memberType);
    }

    /** 특정 scope 보유 여부. */
    public boolean hasScope(String scope) {
        return scopes != null && scopes.contains(scope);
    }

    /** 특정 role 보유 여부. */
    public boolean hasRole(String role) {
        return roles != null && roles.contains(role);
    }
}
