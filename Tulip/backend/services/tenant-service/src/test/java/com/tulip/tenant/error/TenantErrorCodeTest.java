package com.tulip.tenant.error;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * TenantErrorCode 규약 검증.
 *
 * <p>코드 형식 {@code TLP-TNT-{HTTP}-{SEQ}} 및 유니크성을 보장한다.</p>
 */
class TenantErrorCodeTest {

    @Test
    void 모든_코드는_TLP_TNT_접두사를_가진다() {
        for (TenantErrorCode code : TenantErrorCode.values()) {
            assertThat(code.code()).startsWith("TLP-TNT-");
            assertThat(code.httpStatus()).isBetween(400, 599);
            assertThat(code.messageKey()).startsWith("error.tnt.");
        }
    }

    @Test
    void 코드는_유일해야_한다() {
        Set<String> codes = new HashSet<>();
        for (TenantErrorCode code : TenantErrorCode.values()) {
            assertThat(codes.add(code.code())).as("중복 코드: " + code.code()).isTrue();
        }
    }
}
