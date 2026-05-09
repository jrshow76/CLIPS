package com.shelfy.auth.dto.request;

import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
public class SignupRequest {

    @NotBlank(message = "이메일을 입력하세요.")
    @Email(message = "올바른 이메일 형식을 입력하세요.")
    @Size(max = 255, message = "이메일은 255자 이하여야 합니다.")
    private String email;

    @NotBlank(message = "비밀번호를 입력하세요.")
    private String password;

    @NotBlank(message = "비밀번호 확인을 입력하세요.")
    private String passwordConfirm;

    @NotBlank(message = "닉네임을 입력하세요.")
    @Size(min = 2, max = 20, message = "닉네임은 2~20자여야 합니다.")
    @Pattern(regexp = "^[가-힣a-zA-Z0-9_]+$", message = "닉네임은 한글, 영문, 숫자, 언더스코어만 허용합니다.")
    private String nickname;

    @NotNull(message = "이용약관 동의 여부를 확인하세요.")
    private Boolean agreeTerms;

    @NotNull(message = "개인정보 처리방침 동의 여부를 확인하세요.")
    private Boolean agreePrivacy;

    private boolean agreeMarketing;
}
