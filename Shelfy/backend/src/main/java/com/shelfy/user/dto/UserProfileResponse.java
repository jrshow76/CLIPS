package com.shelfy.user.dto;

import com.shelfy.user.entity.User;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@Builder
public class UserProfileResponse {

    private Long userId;
    private String email;
    private String nickname;
    private String bio;
    private String profileImageUrl;
    private boolean emailVerified;
    private boolean agreeMarketing;
    private LocalDateTime createdAt;

    public static UserProfileResponse from(User user) {
        return UserProfileResponse.builder()
                .userId(user.getId())
                .email(user.getEmail())
                .nickname(user.getNickname())
                .bio(user.getBio())
                .profileImageUrl(user.getProfileImageUrl())
                .emailVerified(user.isEmailVerified())
                .agreeMarketing(user.isAgreeMarketing())
                .createdAt(user.getCreatedAt())
                .build();
    }
}
