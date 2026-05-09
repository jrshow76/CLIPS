package com.shelfy.user.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

/**
 * users 테이블 JPA 엔티티
 * <p>
 * 소프트 삭제(deleted_at) 방식을 사용한다.
 * 상태 변경은 도메인 메서드를 통해서만 수행한다 (setter 직접 노출 금지).
 */
@Entity
@Table(name = "users")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 255)
    private String email;

    @Column(nullable = false)
    private String passwordHash;

    @Column(nullable = false, unique = true, length = 50)
    private String nickname;

    @Column(length = 200)
    private String bio;

    @Column(length = 2048)
    private String profileImageUrl;

    @Column(nullable = false)
    private boolean emailVerified = false;

    @Column(nullable = false)
    private boolean agreeTerms = false;

    @Column(nullable = false)
    private boolean agreePrivacy = false;

    @Column(nullable = false)
    private boolean agreeMarketing = false;

    @Column(name = "login_failed_count", nullable = false)
    private int loginFailCount = 0;

    private LocalDateTime lockedUntil;

    @CreationTimestamp
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(nullable = false)
    private LocalDateTime updatedAt;

    private LocalDateTime deletedAt;

    @Builder
    public User(String email, String passwordHash, String nickname,
            boolean agreeTerms, boolean agreePrivacy, boolean agreeMarketing) {
        this.email = email;
        this.passwordHash = passwordHash;
        this.nickname = nickname;
        this.agreeTerms = agreeTerms;
        this.agreePrivacy = agreePrivacy;
        this.agreeMarketing = agreeMarketing;
    }

    // ===== 도메인 메서드 =====

    /** 이메일 인증 완료 처리 */
    public void verifyEmail() {
        this.emailVerified = true;
    }

    /** 로그인 실패 횟수 증가. 5회 초과 시 30분 계정 잠금 */
    public void incrementLoginFailCount(int maxAttempts, int lockDurationMinutes) {
        this.loginFailCount++;
        if (this.loginFailCount >= maxAttempts) {
            this.lockedUntil = LocalDateTime.now().plusMinutes(lockDurationMinutes);
        }
    }

    /** 로그인 성공 시 실패 횟수 초기화 */
    public void resetLoginFailCount() {
        this.loginFailCount = 0;
        this.lockedUntil = null;
    }

    /** 계정 잠금 여부 반환 */
    public boolean isLocked() {
        return lockedUntil != null && LocalDateTime.now().isBefore(lockedUntil);
    }

    /** 탈퇴 처리 (소프트 삭제) */
    public void withdraw() {
        this.deletedAt = LocalDateTime.now();
    }

    /** 탈퇴 여부 반환 */
    public boolean isWithdrawn() {
        return deletedAt != null;
    }

    /** 비밀번호 변경 */
    public void changePassword(String newPasswordHash) {
        this.passwordHash = newPasswordHash;
        this.resetLoginFailCount();
    }

    /** 프로필 수정 */
    public void updateProfile(String nickname, String bio, String profileImageUrl) {
        if (nickname != null) {
            this.nickname = nickname;
        }
        if (bio != null) {
            this.bio = bio;
        }
        if (profileImageUrl != null) {
            this.profileImageUrl = profileImageUrl;
        }
    }
}
