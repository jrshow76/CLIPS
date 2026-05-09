package com.shelfy.auth.service;

import com.shelfy.auth.dto.request.LoginRequest;
import com.shelfy.auth.dto.request.SignupRequest;
import com.shelfy.auth.dto.response.LoginResponse;
import com.shelfy.auth.dto.response.SignupResponse;
import com.shelfy.auth.entity.EmailVerification;
import com.shelfy.auth.entity.RefreshToken;
import com.shelfy.auth.repository.EmailVerificationRepository;
import com.shelfy.auth.repository.RefreshTokenRepository;
import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.security.JwtTokenProvider;
import com.shelfy.user.entity.User;
import com.shelfy.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * 인증 도메인 핵심 비즈니스 로직
 * <p>
 * 트랜잭션 경계:
 * - 클래스 레벨: readOnly = true (기본)
 * - 쓰기 메서드: @Transactional 별도 선언
 */
@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class AuthService {

    // 비밀번호 규칙: 8~20자, 영문+숫자+특수문자 각 1자 이상
    private static final Pattern PASSWORD_PATTERN =
            Pattern.compile("^(?=.*[A-Za-z])(?=.*\\d)(?=.*[!@#$%^&*()_+\\-=\\[\\]{};':\",./<>?]).{8,20}$");

    private final UserRepository userRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final EmailVerificationRepository emailVerificationRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    @Value("${shelfy.max-login-attempts}")
    private int maxLoginAttempts;

    @Value("${shelfy.account-lock-duration-minutes}")
    private int lockDurationMinutes;

    @Value("${shelfy.email-verification-expiry-hours}")
    private int emailVerificationExpiryHours;

    @Value("${jwt.access-token-expiration}")
    private long accessTokenExpirationSeconds;

    @Value("${jwt.refresh-token-expiration}")
    private long refreshTokenExpirationSeconds;

    // ===== 회원가입 =====

    /**
     * 회원가입 처리
     * <p>
     * 1. 이메일/닉네임 중복 검증
     * 2. 비밀번호 규칙 및 일치 여부 검증
     * 3. 필수 동의 여부 검증
     * 4. BCrypt 암호화 후 저장
     */
    @Transactional
    public SignupResponse signup(SignupRequest request) {
        validateSignupRequest(request);

        String encodedPassword = passwordEncoder.encode(request.getPassword());

        User user = User.builder()
                .email(request.getEmail())
                .passwordHash(encodedPassword)
                .nickname(request.getNickname())
                .agreeTerms(request.getAgreeTerms())
                .agreePrivacy(request.getAgreePrivacy())
                .agreeMarketing(request.isAgreeMarketing())
                .build();

        userRepository.save(user);

        // 이메일 인증 토큰 생성 (실제 이메일 발송은 별도 이벤트/서비스로 처리)
        createEmailVerificationToken(user.getId());

        log.info("User registered: userId={}, email={}", user.getId(), user.getEmail());
        return SignupResponse.from(user);
    }

    private void validateSignupRequest(SignupRequest request) {
        // 이메일 중복 검사
        if (userRepository.existsByEmailAndDeletedAtIsNull(request.getEmail())) {
            throw new ShelfyException(ErrorCode.EMAIL_DUPLICATED);
        }

        // 닉네임 중복 검사
        if (userRepository.existsByNicknameAndDeletedAtIsNull(request.getNickname())) {
            throw new ShelfyException(ErrorCode.NICKNAME_DUPLICATED);
        }

        // 비밀번호 규칙 검사
        if (!PASSWORD_PATTERN.matcher(request.getPassword()).matches()) {
            throw new ShelfyException(ErrorCode.PASSWORD_POLICY_VIOLATION);
        }

        // 비밀번호 일치 검사
        if (!request.getPassword().equals(request.getPasswordConfirm())) {
            throw new ShelfyException(ErrorCode.PASSWORD_MISMATCH);
        }

        // 필수 동의 검사
        if (!Boolean.TRUE.equals(request.getAgreeTerms())
                || !Boolean.TRUE.equals(request.getAgreePrivacy())) {
            throw new ShelfyException(ErrorCode.REQUIRED_AGREEMENT_MISSING);
        }
    }

    // ===== 로그인 =====

    /**
     * 로그인 처리
     * <p>
     * 1. 이메일로 사용자 조회
     * 2. 탈퇴/잠금 상태 확인
     * 3. 비밀번호 검증
     * 4. 실패 횟수 처리 (5회 초과 시 계정 잠금)
     * 5. Access Token + Refresh Token 발급
     *
     * @return [accessToken, rawRefreshToken] 쌍
     */
    @Transactional
    public String[] login(LoginRequest request) {
        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new ShelfyException(ErrorCode.LOGIN_FAILED));

        // 탈퇴 계정 확인
        if (user.isWithdrawn()) {
            throw new ShelfyException(ErrorCode.ACCOUNT_WITHDRAWN);
        }

        // 계정 잠금 확인
        if (user.isLocked()) {
            throw new ShelfyException(ErrorCode.ACCOUNT_LOCKED);
        }

        // 비밀번호 검증
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            user.incrementLoginFailCount(maxLoginAttempts, lockDurationMinutes);
            userRepository.save(user);
            log.warn("Login failed: email={}, failCount={}", user.getEmail(), user.getLoginFailCount());
            throw new ShelfyException(ErrorCode.LOGIN_FAILED);
        }

        // 로그인 성공: 실패 횟수 초기화
        user.resetLoginFailCount();
        userRepository.save(user);

        // 토큰 발급
        String accessToken = jwtTokenProvider.generateAccessToken(
                user.getId(), user.getEmail(), user.getNickname(), user.isEmailVerified());

        String rawRefreshToken = generateAndSaveRefreshToken(user.getId());

        log.info("User logged in: userId={}", user.getId());
        return new String[]{accessToken, rawRefreshToken};
    }

    // ===== 토큰 갱신 =====

    /**
     * Refresh Token으로 새 Access Token 발급
     * <p>
     * Raw 토큰을 SHA-256 해시하여 DB와 비교한다.
     *
     * @return 새 accessToken
     */
    @Transactional
    public String refreshAccessToken(String rawRefreshToken) {
        String tokenHash = hashToken(rawRefreshToken);

        RefreshToken refreshToken = refreshTokenRepository.findValidByTokenHash(tokenHash)
                .orElseThrow(() -> new ShelfyException(ErrorCode.REFRESH_TOKEN_INVALID));

        if (!refreshToken.isValid()) {
            throw new ShelfyException(ErrorCode.REFRESH_TOKEN_EXPIRED);
        }

        User user = userRepository.findActiveById(refreshToken.getUserId())
                .orElseThrow(() -> new ShelfyException(ErrorCode.REFRESH_TOKEN_INVALID));

        return jwtTokenProvider.generateAccessToken(
                user.getId(), user.getEmail(), user.getNickname(), user.isEmailVerified());
    }

    // ===== 로그아웃 =====

    /**
     * 로그아웃: 사용자의 모든 Refresh Token 무효화
     */
    @Transactional
    public void logout(Long userId) {
        refreshTokenRepository.revokeAllByUserId(userId);
        log.info("User logged out: userId={}", userId);
    }

    /**
     * 특정 Refresh Token만 무효화 (쿠키에서 추출한 토큰)
     */
    @Transactional
    public void logoutWithToken(Long userId, String rawRefreshToken) {
        String tokenHash = hashToken(rawRefreshToken);
        refreshTokenRepository.findValidByTokenHash(tokenHash)
                .ifPresent(RefreshToken::revoke);
        log.info("User logged out with specific token: userId={}", userId);
    }

    // ===== 이메일 인증 =====

    /**
     * 이메일 인증 처리
     */
    @Transactional
    public void verifyEmail(String token) {
        EmailVerification verification = emailVerificationRepository.findByToken(token)
                .orElseThrow(() -> new ShelfyException(ErrorCode.EMAIL_VERIFICATION_TOKEN_INVALID));

        if (verification.isVerified()) {
            throw new ShelfyException(ErrorCode.EMAIL_ALREADY_VERIFIED);
        }

        if (verification.isExpired()) {
            throw new ShelfyException(ErrorCode.EMAIL_VERIFICATION_TOKEN_EXPIRED);
        }

        verification.verify();
        emailVerificationRepository.save(verification);

        User user = userRepository.findActiveById(verification.getUserId())
                .orElseThrow(() -> new ShelfyException(ErrorCode.EMAIL_VERIFICATION_TOKEN_INVALID));
        user.verifyEmail();
        userRepository.save(user);

        log.info("Email verified: userId={}", user.getId());
    }

    /**
     * 이메일 인증 토큰 재발송 요청
     */
    @Transactional
    public void resendVerificationEmail(Long userId) {
        User user = userRepository.findActiveById(userId)
                .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));

        if (user.isEmailVerified()) {
            throw new ShelfyException(ErrorCode.EMAIL_ALREADY_VERIFIED);
        }

        createEmailVerificationToken(userId);
        // TODO: 실제 이메일 발송 서비스 연동
        log.info("Verification email resent: userId={}", userId);
    }

    // ===== 내부 헬퍼 메서드 =====

    /**
     * 이메일 인증 토큰 생성 및 저장
     */
    private void createEmailVerificationToken(Long userId) {
        String token = UUID.randomUUID().toString().replace("-", "");
        LocalDateTime expiresAt = LocalDateTime.now().plusHours(emailVerificationExpiryHours);

        EmailVerification verification = EmailVerification.builder()
                .userId(userId)
                .token(token)
                .expiresAt(expiresAt)
                .build();

        emailVerificationRepository.save(verification);
        // TODO: 이메일 발송 이벤트 publish
    }

    /**
     * Raw Refresh Token 생성 → SHA-256 해시 → DB 저장
     *
     * @return rawRefreshToken (클라이언트에 쿠키로 전달)
     */
    private String generateAndSaveRefreshToken(Long userId) {
        String rawToken = UUID.randomUUID().toString().replace("-", "")
                + UUID.randomUUID().toString().replace("-", "");
        String tokenHash = hashToken(rawToken);
        LocalDateTime expiresAt = LocalDateTime.now().plusSeconds(refreshTokenExpirationSeconds);

        RefreshToken refreshToken = RefreshToken.builder()
                .userId(userId)
                .tokenHash(tokenHash)
                .expiresAt(expiresAt)
                .build();

        refreshTokenRepository.save(refreshToken);
        return rawToken;
    }

    /**
     * SHA-256 해시 처리
     */
    private String hashToken(String rawToken) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(rawToken.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new ShelfyException(ErrorCode.INTERNAL_SERVER_ERROR);
        }
    }

}
