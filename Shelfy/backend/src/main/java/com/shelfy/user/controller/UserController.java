package com.shelfy.user.controller;

import com.shelfy.common.response.ApiResponse;
import com.shelfy.security.CustomUserDetails;
import com.shelfy.user.dto.ChangePasswordRequest;
import com.shelfy.user.dto.UpdateProfileRequest;
import com.shelfy.user.dto.UserProfileResponse;
import com.shelfy.user.dto.WithdrawRequest;
import com.shelfy.user.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

/**
 * 사용자 마이페이지 API 컨트롤러
 * <p>
 * 담당: BackendDev (프로필 조회/수정/비밀번호 변경/탈퇴)
 * 셀러 공개 프로필, 수익 현황은 SellerController에서 처리
 */
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    /**
     * GET /api/v1/users/me
     * 내 프로필 조회
     */
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<UserProfileResponse>> getMyProfile(
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        UserProfileResponse response = userService.getMyProfile(userDetails.getUserId());
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * PUT /api/v1/users/me
     * 내 프로필 수정 (닉네임/소개/프로필 이미지)
     */
    @PutMapping("/me")
    public ResponseEntity<ApiResponse<UserProfileResponse>> updateProfile(
            @RequestBody @Valid UpdateProfileRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        UserProfileResponse response = userService.updateProfile(userDetails.getUserId(), request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * PUT /api/v1/users/me/password
     * 비밀번호 변경
     */
    @PutMapping("/me/password")
    public ResponseEntity<Void> changePassword(
            @RequestBody @Valid ChangePasswordRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        userService.changePassword(userDetails.getUserId(), request);
        return ResponseEntity.noContent().build();
    }

    /**
     * DELETE /api/v1/users/me
     * 회원 탈퇴 (소프트 삭제)
     */
    @DeleteMapping("/me")
    public ResponseEntity<Void> withdraw(
            @RequestBody @Valid WithdrawRequest request,
            @AuthenticationPrincipal CustomUserDetails userDetails) {

        userService.withdraw(userDetails.getUserId(), request);
        return ResponseEntity.noContent().build();
    }
}
