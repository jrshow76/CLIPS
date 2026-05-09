package com.shelfy.user.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.user.dto.ChangePasswordRequest;
import com.shelfy.user.dto.UpdateProfileRequest;
import com.shelfy.user.dto.UserProfileResponse;
import com.shelfy.user.dto.WithdrawRequest;
import com.shelfy.user.entity.User;
import com.shelfy.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 사용자 마이페이지 서비스
 * <p>
 * 클래스 레벨 readOnly = true 적용.
 * 쓰기 작업 메서드에만 @Transactional 별도 선언.
 */
@Slf4j
@Service
@Transactional(readOnly = true)
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    /**
     * 내 프로필 조회
     *
     * @param userId 요청자 ID (JWT에서 추출)
     * @return 사용자 프로필 응답 DTO
     */
    public UserProfileResponse getMyProfile(Long userId) {
        User user = findActiveUser(userId);
        return UserProfileResponse.from(user);
    }

    /**
     * 내 프로필 수정 (닉네임/소개/프로필 이미지)
     *
     * @param userId  요청자 ID
     * @param request 수정 요청 DTO
     * @return 수정된 프로필 응답 DTO
     */
    @Transactional
    public UserProfileResponse updateProfile(Long userId, UpdateProfileRequest request) {
        User user = findActiveUser(userId);

        // 닉네임 변경 시 중복 확인
        if (request.getNickname() != null
                && !request.getNickname().equals(user.getNickname())) {
            if (userRepository.existsByNicknameExcludingUser(request.getNickname(), userId)) {
                throw new ShelfyException(ErrorCode.NICKNAME_DUPLICATED);
            }
        }

        user.updateProfile(request.getNickname(), request.getBio(), request.getProfileImageUrl());
        log.info("프로필 수정 완료: userId={}", userId);

        return UserProfileResponse.from(user);
    }

    /**
     * 비밀번호 변경
     *
     * @param userId  요청자 ID
     * @param request 비밀번호 변경 요청 DTO
     */
    @Transactional
    public void changePassword(Long userId, ChangePasswordRequest request) {
        User user = findActiveUser(userId);

        // 현재 비밀번호 확인
        if (!passwordEncoder.matches(request.getCurrentPassword(), user.getPasswordHash())) {
            throw new ShelfyException(ErrorCode.PASSWORD_MISMATCH);
        }

        // 새 비밀번호와 확인 비밀번호 일치 확인
        if (!request.getNewPassword().equals(request.getNewPasswordConfirm())) {
            throw new ShelfyException(ErrorCode.PASSWORD_MISMATCH);
        }

        String encodedNewPassword = passwordEncoder.encode(request.getNewPassword());
        user.changePassword(encodedNewPassword);
        log.info("비밀번호 변경 완료: userId={}", userId);
    }

    /**
     * 회원 탈퇴 (소프트 삭제)
     *
     * @param userId  요청자 ID
     * @param request 탈퇴 요청 DTO (비밀번호 재확인)
     */
    @Transactional
    public void withdraw(Long userId, WithdrawRequest request) {
        User user = findActiveUser(userId);

        // 현재 비밀번호 재확인
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new ShelfyException(ErrorCode.PASSWORD_MISMATCH);
        }

        user.withdraw();
        log.info("회원 탈퇴 처리 완료: userId={}", userId);
    }

    // ===== private 헬퍼 메서드 =====

    private User findActiveUser(Long userId) {
        return userRepository.findActiveById(userId)
                .orElseThrow(() -> new ShelfyException(ErrorCode.RESOURCE_NOT_FOUND));
    }
}
