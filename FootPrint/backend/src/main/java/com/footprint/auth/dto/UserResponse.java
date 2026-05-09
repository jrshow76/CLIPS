package com.footprint.auth.dto;

import com.footprint.auth.entity.User;

import java.util.UUID;

public record UserResponse(
        UUID id,
        String email,
        String nickname,
        String profileImageUrl
) {
    public static UserResponse from(User user) {
        return new UserResponse(
                user.getId(),
                user.getEmail(),
                user.getNickname(),
                user.getProfileImageUrl()
        );
    }
}
