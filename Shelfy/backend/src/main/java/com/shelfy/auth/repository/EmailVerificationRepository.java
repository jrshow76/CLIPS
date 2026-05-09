package com.shelfy.auth.repository;

import com.shelfy.auth.entity.EmailVerification;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface EmailVerificationRepository extends JpaRepository<EmailVerification, Long> {

    /**
     * 토큰 값으로 인증 레코드 조회
     */
    Optional<EmailVerification> findByToken(String token);

    /**
     * 사용자의 가장 최근 미인증 토큰 조회 (재발송 시 중복 방지)
     */
    @Query("SELECT ev FROM EmailVerification ev WHERE ev.userId = :userId AND ev.verifiedAt IS NULL ORDER BY ev.createdAt DESC")
    Optional<EmailVerification> findLatestUnverifiedByUserId(@Param("userId") Long userId);
}
