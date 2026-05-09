package com.shelfy.auth.repository;

import com.shelfy.auth.entity.RefreshToken;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface RefreshTokenRepository extends JpaRepository<RefreshToken, Long> {

    /**
     * 해시값으로 유효한 Refresh Token 조회
     */
    @Query("SELECT rt FROM RefreshToken rt WHERE rt.tokenHash = :tokenHash AND rt.revokedAt IS NULL")
    Optional<RefreshToken> findValidByTokenHash(@Param("tokenHash") String tokenHash);

    /**
     * 사용자의 모든 Refresh Token 무효화 (로그아웃, 비밀번호 변경 시)
     */
    @Modifying
    @Query("UPDATE RefreshToken rt SET rt.revokedAt = CURRENT_TIMESTAMP WHERE rt.userId = :userId AND rt.revokedAt IS NULL")
    void revokeAllByUserId(@Param("userId") Long userId);
}
