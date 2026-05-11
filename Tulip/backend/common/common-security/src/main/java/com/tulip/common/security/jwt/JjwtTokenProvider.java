package com.tulip.common.security.jwt;

import com.tulip.common.security.principal.TulipUserPrincipal;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;

import java.security.Key;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * jjwt 라이브러리 기반 {@link JwtTokenProvider} 구현 (검증 전용).
 *
 * <p>Phase 1-A 에서는 단일 대칭/공개키만 처리한다.
 * 운영에서는 service-auth 의 JWKS 엔드포인트와 결합하는 별도 구현체로 교체된다.</p>
 */
public class JjwtTokenProvider implements JwtTokenProvider {

    private final Key verificationKey;

    public JjwtTokenProvider(Key verificationKey) {
        this.verificationKey = verificationKey;
    }

    @Override
    public TulipUserPrincipal validateAndExtract(String token) {
        Claims claims = parse(token).getPayload();
        return toPrincipal(claims);
    }

    @Override
    public boolean isExpired(String token) {
        try {
            Date exp = parse(token).getPayload().getExpiration();
            return exp != null && exp.before(new Date());
        } catch (ExpiredJwtException e) {
            return true;
        } catch (JwtException e) {
            return true;
        }
    }

    @Override
    public String tokenId(String token) {
        try {
            return parse(token).getPayload().getId();
        } catch (JwtException e) {
            return null;
        }
    }

    private io.jsonwebtoken.Jws<Claims> parse(String token) {
        return Jwts.parser()
                .verifyWith((javax.crypto.SecretKey) verificationKey)
                .build()
                .parseSignedClaims(token);
    }

    @SuppressWarnings("unchecked")
    private static TulipUserPrincipal toPrincipal(Claims claims) {
        Object rolesClaim = claims.get("roles");
        Object scopesClaim = claims.get("scopes");
        Object libraryIdsClaim = claims.get("libraryIds");

        Set<String> roles = new HashSet<>();
        if (rolesClaim instanceof List<?> list) {
            list.forEach(r -> roles.add(String.valueOf(r)));
        }
        Set<String> scopes = new HashSet<>();
        if (scopesClaim instanceof List<?> list) {
            list.forEach(s -> scopes.add(String.valueOf(s)));
        }
        List<String> libraryIds = libraryIdsClaim instanceof List<?> list
                ? ((List<?>) list).stream().map(String::valueOf).toList()
                : List.of();

        return new TulipUserPrincipal(
                claims.getSubject(),
                stringClaim(claims, "tenantId"),
                libraryIds,
                stringClaim(claims, "primaryBranchId"),
                roles,
                scopes,
                stringClaim(claims, "memberType"),
                stringClaim(claims, "deviceId"),
                claims.getId()
        );
    }

    private static String stringClaim(Claims claims, String key) {
        Object v = claims.get(key);
        return v == null ? null : String.valueOf(v);
    }
}
