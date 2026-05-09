package com.shelfy.order.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class RefundRequest {

    @NotBlank(message = "환불 사유는 필수입니다.")
    @Size(max = 500, message = "환불 사유는 500자 이내여야 합니다.")
    private String reason;
}
