package com.tulip.iam.security;

import com.tulip.common.security.jwt.JtiBlacklistChecker;
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
 * IAM 서비스 내부에서 사용하는 Bearer 토큰 인증 필터.
 *
 * <p>JWKS 검증 + JTI 블랙리스트 검사 + Spring Security Authentication 객체 설정까지 수행한다.
 * 라이브러리화하지 않은 이유는 Gateway 가 reactive 이고 본 서비스는 servlet 이라 SPI 가
 * 분리되기 때문이다. 토큰 검증 로직은 공통 모듈({@code common-security})을 사용한다.</p>
 */
@Component
public class IamBearerAuthenticationFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(IamBearerAuthenticationFilter.class);
    private static final String BEARER = "Bearer ";

    private final JwtTokenProvider provider;
    private final JtiBlacklistChecker blacklist;

    public IamBearerAuthenticationFilter(JwtTokenProvider provider, JtiBlacklistChecker blacklist) {
        this.provider = provider;
        this.blacklist = blacklist;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String header = request.getHeader("Authorization");
        if (header == null || !header.startsWith(BEARER)) {
            chain.doFilter(request, response);
            return;
        }
        String token = header.substring(BEARER.length()).trim();
        try {
            TulipUserPrincipal principal = provider.validateAndExtract(token);
            if (principal.tokenId() != null && blacklist.isBlacklisted(principal.tokenId())) {
                log.info("블랙리스트 JTI 차단 jti={} sub={}", principal.tokenId(), principal.userId());
                chain.doFilter(request, response);
                return;
            }
            SecurityContextHolder.getContext().setAuthentication(toAuthentication(principal));
        } catch (RuntimeException ex) {
            log.debug("JWT 검증 실패 — 익명 처리 cause={}", ex.getMessage());
            // 인증 실패는 EntryPoint 가 처리하도록 SecurityContext 비움
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
