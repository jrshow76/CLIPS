package com.tulip.common.security.jwt;

/**
 * JWT JTI 블랙리스트 검사기.
 *
 * <p>{@code 05_security_and_auth.md} §2.5 — 로그아웃·이상탐지·강제차단 시 Access/Refresh
 * 토큰의 jti 를 Redis 블랙리스트에 등록한다. 본 인터페이스는 검증 측(Gateway·Resource Server)이
 * 검사할 SPI 이며, 구현체는 iam-service/api-gateway 각각 자체 Redis 백엔드로 보유한다.</p>
 *
 * <p>실패 시 처리는 호출부 책임(차단/통과)이며, 본 SPI 는 단순히 boolean 만 반환한다.</p>
 */
public interface JtiBlacklistChecker {

    /** 해당 jti 가 블랙리스트에 등록되어 있으면 {@code true}. */
    boolean isBlacklisted(String jti);

    /** 항상 통과(허용)하는 no-op 구현. 테스트·로컬 fallback 용. */
    JtiBlacklistChecker ALLOW_ALL = jti -> false;
}
