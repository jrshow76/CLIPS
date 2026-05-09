package com.shelfy.user.service;

import com.shelfy.common.exception.ErrorCode;
import com.shelfy.common.exception.ShelfyException;
import com.shelfy.user.dto.ChangePasswordRequest;
import com.shelfy.user.dto.UpdateProfileRequest;
import com.shelfy.user.dto.UserProfileResponse;
import com.shelfy.user.dto.WithdrawRequest;
import com.shelfy.user.entity.User;
import com.shelfy.user.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
@DisplayName("UserService 단위 테스트")
class UserServiceTest {

    @InjectMocks
    private UserService userService;

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    // ===== getMyProfile 테스트 =====

    @Test
    @DisplayName("내 프로필 조회 - 정상 케이스")
    void getMyProfile_success() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "testuser", "인코딩된비밀번호");

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));

        // when
        UserProfileResponse response = userService.getMyProfile(userId);

        // then
        assertThat(response.getUserId()).isEqualTo(userId);
        assertThat(response.getEmail()).isEqualTo("test@example.com");
        assertThat(response.getNickname()).isEqualTo("testuser");
    }

    @Test
    @DisplayName("탈퇴한 사용자 프로필 조회 - RESOURCE_NOT_FOUND 예외 발생")
    void getMyProfile_withdrawnUser_throwsException() {
        // given
        Long userId = 1L;
        given(userRepository.findActiveById(userId)).willReturn(Optional.empty());

        // when & then
        assertThatThrownBy(() -> userService.getMyProfile(userId))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.RESOURCE_NOT_FOUND);
    }

    // ===== updateProfile 테스트 =====

    @Test
    @DisplayName("프로필 수정 - 닉네임 변경 성공")
    void updateProfile_changeNickname_success() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "oldNick", "인코딩된비밀번호");
        UpdateProfileRequest request = new UpdateProfileRequest("newNick", null, null);

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));
        given(userRepository.existsByNicknameExcludingUser("newNick", userId)).willReturn(false);

        // when
        UserProfileResponse response = userService.updateProfile(userId, request);

        // then
        assertThat(response.getNickname()).isEqualTo("newNick");
    }

    @Test
    @DisplayName("프로필 수정 - 닉네임 중복 시 AUTH-E002 예외 발생")
    void updateProfile_duplicateNickname_throwsException() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "oldNick", "인코딩된비밀번호");
        UpdateProfileRequest request = new UpdateProfileRequest("existingNick", null, null);

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));
        given(userRepository.existsByNicknameExcludingUser("existingNick", userId)).willReturn(true);

        // when & then
        assertThatThrownBy(() -> userService.updateProfile(userId, request))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.NICKNAME_DUPLICATED);
    }

    @Test
    @DisplayName("프로필 수정 - 동일 닉네임으로 변경 시 중복 체크 없음")
    void updateProfile_sameNickname_noCheck() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "sameNick", "인코딩된비밀번호");
        UpdateProfileRequest request = new UpdateProfileRequest("sameNick", "새 소개", null);

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));

        // when
        UserProfileResponse response = userService.updateProfile(userId, request);

        // then: 중복 체크 메서드가 호출되지 않아야 함
        assertThat(response.getBio()).isEqualTo("새 소개");
    }

    // ===== changePassword 테스트 =====

    @Test
    @DisplayName("비밀번호 변경 - 정상 케이스")
    void changePassword_success() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "testuser", "인코딩된현재비밀번호");
        ChangePasswordRequest request = new ChangePasswordRequest(
                "현재비밀번호", "NewPassword1!", "NewPassword1!");

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));
        given(passwordEncoder.matches("현재비밀번호", "인코딩된현재비밀번호")).willReturn(true);
        given(passwordEncoder.encode("NewPassword1!")).willReturn("인코딩된새비밀번호");

        // when
        userService.changePassword(userId, request);

        // then
        verify(passwordEncoder).encode("NewPassword1!");
    }

    @Test
    @DisplayName("비밀번호 변경 - 현재 비밀번호 불일치 시 AUTH-E003 예외 발생")
    void changePassword_wrongCurrentPassword_throwsException() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "testuser", "인코딩된비밀번호");
        ChangePasswordRequest request = new ChangePasswordRequest(
                "틀린비밀번호", "NewPassword1!", "NewPassword1!");

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));
        given(passwordEncoder.matches("틀린비밀번호", "인코딩된비밀번호")).willReturn(false);

        // when & then
        assertThatThrownBy(() -> userService.changePassword(userId, request))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.PASSWORD_MISMATCH);
    }

    @Test
    @DisplayName("비밀번호 변경 - 새 비밀번호 확인 불일치 시 AUTH-E003 예외 발생")
    void changePassword_newPasswordMismatch_throwsException() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "testuser", "인코딩된비밀번호");
        ChangePasswordRequest request = new ChangePasswordRequest(
                "현재비밀번호", "NewPassword1!", "DifferentPassword1!");

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));
        given(passwordEncoder.matches("현재비밀번호", "인코딩된비밀번호")).willReturn(true);

        // when & then
        assertThatThrownBy(() -> userService.changePassword(userId, request))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.PASSWORD_MISMATCH);
    }

    // ===== withdraw 테스트 =====

    @Test
    @DisplayName("회원 탈퇴 - 정상 케이스")
    void withdraw_success() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "testuser", "인코딩된비밀번호");
        WithdrawRequest request = new WithdrawRequest("현재비밀번호");

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));
        given(passwordEncoder.matches("현재비밀번호", "인코딩된비밀번호")).willReturn(true);

        // when
        userService.withdraw(userId, request);

        // then: 탈퇴 처리 후 deletedAt이 설정되어야 함
        assertThat(user.isWithdrawn()).isTrue();
    }

    @Test
    @DisplayName("회원 탈퇴 - 비밀번호 불일치 시 AUTH-E003 예외 발생")
    void withdraw_wrongPassword_throwsException() {
        // given
        Long userId = 1L;
        User user = buildUser(userId, "test@example.com", "testuser", "인코딩된비밀번호");
        WithdrawRequest request = new WithdrawRequest("틀린비밀번호");

        given(userRepository.findActiveById(userId)).willReturn(Optional.of(user));
        given(passwordEncoder.matches("틀린비밀번호", "인코딩된비밀번호")).willReturn(false);

        // when & then
        assertThatThrownBy(() -> userService.withdraw(userId, request))
                .isInstanceOf(ShelfyException.class)
                .extracting(e -> ((ShelfyException) e).getErrorCode())
                .isEqualTo(ErrorCode.PASSWORD_MISMATCH);
    }

    // ===== 테스트 픽스처 헬퍼 메서드 =====

    private User buildUser(Long userId, String email, String nickname, String passwordHash) {
        return User.builder()
                .email(email)
                .passwordHash(passwordHash)
                .nickname(nickname)
                .agreeTerms(true)
                .agreePrivacy(true)
                .agreeMarketing(false)
                .build();
    }
}
