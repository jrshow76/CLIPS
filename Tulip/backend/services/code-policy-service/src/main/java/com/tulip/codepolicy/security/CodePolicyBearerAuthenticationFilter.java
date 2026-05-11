package com.tulip.codepolicy.security;

import com.tulip.common.security.jwt.JwtTokenProvider;
import com.tulip.common.security.principal.TulipUserPrincipal;
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
 * Bearer JWT 검증 필터.
 */
@Component
public class CodePolicyBearerAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(CodePolicyBearerAuthenticationFilter.class);
    private static final String BEARER = "Bearer ";

    private final JwtTokenProvider provider;

    public CodePolicyBearerAuthenticationFilter(JwtTokenProvider provider) {
        this.provider = provider;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith(BEARER)) {
            String token = header.substring(BEARER.length()).trim();
            try {
                TulipUserPrincipal principal = provider.validateAndExtract(token);
                SecurityContextHolder.getContext().setAuthentication(toAuthentication(principal));
            } catch (RuntimeException ex) {
                log.debug("JWT 검증 실패 — 익명 처리 cause={}", ex.getMessage());
            }
        }
        chain.doFilter(request, response);
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
}
