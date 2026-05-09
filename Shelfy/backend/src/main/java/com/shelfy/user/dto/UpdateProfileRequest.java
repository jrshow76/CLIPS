package com.shelfy.user.dto;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class UpdateProfileRequest {

    @Size(min = 2, max = 20, message = "닉네임은 2~20자여야 합니다.")
    private String nickname;

    @Size(max = 200, message = "소개 문구는 200자 이내여야 합니다.")
    private String bio;

    /** 프로필 이미지 업로드 후 반환된 URL */
    private String profileImageUrl;
}
