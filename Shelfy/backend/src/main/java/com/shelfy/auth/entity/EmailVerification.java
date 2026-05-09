package com.shelfy.auth.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * email_verifications 테이블 JPA 엔티티
 * <p>
 * 이메일 인증 링크 토큰을 관리한다.
 * 유효 시간: 24시간, 인증 완료 시 verified_at 기록.
 */
@Entity
@Table(name = "email_verifications")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class EmailVerification {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long userId;

    @Column(nullable = false, unique = true, length = 64)
    private String token;

    @Column(nullable = false)
    private LocalDateTime expiresAt;

    private LocalDateTime verifiedAt;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Builder
    public EmailVerification(Long userId, String token, LocalDateTime expiresAt) {
        this.userId = userId;
        this.token = token;
        this.expiresAt = expiresAt;
    }

    /** 인증 완료 처리 */
    public void verify() {
        this.verifiedAt = LocalDateTime.now();
    }

    /** 이미 인증 완료 여부 */
    public boolean isVerified() {
        return verifiedAt != null;
    }

    /** 토큰 만료 여부 */
    public boolean isExpired() {
        return LocalDateTime.now().isAfter(expiresAt);
    }
}
