package com.tulip.tenant.security;

import com.tulip.common.security.jwt.JwtTokenProvider;
import com.tulip.common.security.principal.TulipUserPrincipal;
import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;

/**
 * tenant-service 전용 Bearer 토큰 인증 필터.
 *
 * <p>역할:
 *  1. JWT 검증(JWKS) 후 Spring Security 인증 객체 설정
 *  2. {@link TenantContextHolder} 에 tenantId/userId 적재
 *  3. {@link TenantSessionContext} 에 RLS 적용용 정보 적재
 *  4. SYS_ADMIN 토큰 + {@code X-Sys-Bypass: true} 헤더 조합이면 bypass 모드 진입.</p>
 */
@Component
public class TenantAuthFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(TenantAuthFilter.class);
    private static final String BEARER = "Bearer ";
    public static final String HEADER_SYS_BYPASS = "X-Sys-Bypass";

    private final JwtTokenProvider provider;

    public TenantAuthFilter(JwtTokenProvider provider) {
        this.provider = provider;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header == null || !header.startsWith(BEARER)) {
            try {
                chain.doFilter(request, response);
            } finally {
                clear();
            }
            return;
        }
        String token = header.substring(BEARER.length()).trim();
        try {
            TulipUserPrincipal principal = provider.validateAndExtract(token);
            SecurityContextHolder.getContext().setAuthentication(toAuthentication(principal));
            applyContext(principal, request);
        } catch (RuntimeException ex) {
            log.debug("JWT 검증 실패 — 익명 처리 cause={}", ex.getMessage());
        }
        try {
            chain.doFilter(request, response);
        } finally {
            clear();
        }
    }

    private void applyContext(TulipUserPrincipal principal, HttpServletRequest request) {
        boolean bypass = principal.hasRole("SYS_ADMIN")
                && "true".equalsIgnoreCase(request.getHeader(HEADER_SYS_BYPASS));
        TenantContext ctx = new TenantContext(
                principal.tenantId(),
                principal.primaryLibraryId(),
                principal.userId(),
                principal.memberType(),
                principal.hasRole("SYS_ADMIN")
        );
        TenantContextHolder.set(ctx);

        Long tenantIdNum = parseLong(principal.tenantId());
        String role = pickRole(principal);
        TenantSessionContext.set(tenantIdNum, role, bypass);
    }

    private static String pickRole(TulipUserPrincipal principal) {
        if (principal.hasRole("SYS_ADMIN")) return "SYS_ADMIN";
        if (principal.hasRole("TENANT_ADMIN")) return "TENANT_ADMIN";
        if (principal.hasRole("LIB_ADMIN")) return "LIB_ADMIN";
        return "USER";
    }

    private void clear() {
        TenantContextHolder.clear();
        TenantSessionContext.clear();
        SecurityContextHolder.clearContext();
    }

    private static AbstractAuthenticationToken toAuthentication(TulipUserPrincipal principal) {
        Collection<GrantedAuthority> authorities = new ArrayList<>();
        if (principal.roles() != null) {
            principal.roles().forEach(r -> authorities.add(new SimpleGrantedAuthority("ROLE_" + r)));
        }
        if (principal.scopes() != null) {
            principal.scopes().forEach(s -> authorities.add(new SimpleGrantedAuthority("SCOPE_" + s)));
        }
        AbstractAuthenticationToken token = new AbstractAuthenticationToken(authorities) {
            @Override public Object getCredentials() { return ""; }
            @Override public Object getPrincipal() { return principal; }
        };
        token.setAuthenticated(true);
        return token;
    }

    private static Long parseLong(String value) {
        if (value == null || value.isBlank()) return null;
        try { return Long.parseLong(value); } catch (NumberFormatException e) { return null; }
    }
}
