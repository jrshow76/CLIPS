package com.footprint.auth.service;

import com.footprint.auth.dto.LoginRequest;
import com.footprint.auth.dto.SignupRequest;
import com.footprint.auth.dto.TokenResponse;
import com.footprint.auth.dto.UserResponse;
import com.footprint.auth.entity.User;
import com.footprint.auth.repository.UserRepository;
import com.footprint.auth.repository.RefreshTokenRepository;
import com.footprint.auth.entity.RefreshToken;
import com.footprint.common.exception.CustomException;
import com.footprint.common.exception.ErrorCode;
import com.footprint.common.security.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.util.HexFormat;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AuthService {

    private final UserRepository userRepository;
    private final RefreshTokenRepository refreshTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    @Value("${jwt.refresh-token-expiry-ms}")
    private long refreshTokenExpiryMs;

    @Transactional
    public void signup(SignupRequest request) {
        if (userRepository.existsByEmailAndDeletedAtIsNull(request.email())) {
            throw new CustomException(ErrorCode.EMAIL_ALREADY_EXISTS);
        }
        User user = User.builder()
                .email(request.email())
                .passwordHash(passwordEncoder.encode(request.password()))
                .nickname(request.nickname())
                .build();
        userRepository.save(user);
    }

    @Transactional
    public TokenResponse login(LoginRequest request) {
        User user = userRepository.findByEmailAndDeletedAtIsNull(request.email())
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_CREDENTIALS));

        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new CustomException(ErrorCode.INVALID_CREDENTIALS);
        }

        return issueTokens(user.getId());
    }

    @Transactional
    public TokenResponse refresh(String rawRefreshToken) {
        String hash = sha256(rawRefreshToken);
        RefreshToken stored = refreshTokenRepository.findByTokenHashAndRevokedAtIsNull(hash)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_TOKEN));

        if (stored.getExpiresAt().isBefore(OffsetDateTime.now())) {
            throw new CustomException(ErrorCode.EXPIRED_TOKEN);
        }

        stored.revoke();
        return issueTokens(stored.getUserId());
    }

    public UserResponse getMe(UUID userId) {
        User user = userRepository.findById(userId)
                .filter(User::isActive)
                .orElseThrow(() -> new CustomException(ErrorCode.UNAUTHORIZED));
        return UserResponse.from(user);
    }

    @Transactional
    public void logout(String rawRefreshToken) {
        String hash = sha256(rawRefreshToken);
        refreshTokenRepository.findByTokenHashAndRevokedAtIsNull(hash)
                .ifPresent(RefreshToken::revoke);
    }

    private TokenResponse issueTokens(UUID userId) {
        String accessToken  = jwtTokenProvider.generateAccessToken(userId);
        String refreshToken = jwtTokenProvider.generateRefreshToken(userId);

        RefreshToken entity = RefreshToken.builder()
                .userId(userId)
                .tokenHash(sha256(refreshToken))
                .expiresAt(OffsetDateTime.now().plusSeconds(refreshTokenExpiryMs / 1000))
                .build();
        refreshTokenRepository.save(entity);

        return new TokenResponse(accessToken, refreshToken, refreshTokenExpiryMs);
    }

    private String sha256(String raw) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(raw.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }
}
