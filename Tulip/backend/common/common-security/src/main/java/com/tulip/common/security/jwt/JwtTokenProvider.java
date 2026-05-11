package com.tulip.common.security.jwt;

import com.tulip.common.security.principal.TulipUserPrincipal;

/**
 * JWT 검증/파싱 진입점.
 *
 * <p>Phase 1-A 본 모듈은 검증만 책임지며, 토큰 발급은 Phase 1-B 의 {@code service-auth} 에서 담당한다.
 * 알고리즘 RS256, JWKS 기반 공개키 분산 검증 (05_security_and_auth.md §2.5).</p>
 */
public interface JwtTokenProvider {

    /** 토큰의 서명/만료/필수 클레임을 검증한다. 실패 시 예외. */
    TulipUserPrincipal validateAndExtract(String token);

    /** 토큰이 만료되었는지 빠르게 확인 (서명 검증 없이). */
    boolean isExpired(String token);

    /** 토큰의 jti 값을 반환 (블랙리스트 검사용). */
    String tokenId(String token);
}
