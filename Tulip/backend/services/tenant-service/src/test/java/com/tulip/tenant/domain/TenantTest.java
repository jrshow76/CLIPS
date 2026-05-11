package com.tulip.tenant.domain;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Tenant 도메인 비즈니스 규칙 단위 테스트.
 */
class TenantTest {

    @Test
    void create_은_ACTIVE_상태_와_기본플랜으로_초기화된다() {
        Tenant t = Tenant.create("01HABCDE", "demo", "데모", null, 99L);

        assertThat(t.getStatus()).isEqualTo(TenantStatus.ACTIVE);
        assertThat(t.getPlan()).isEqualTo("STANDARD");
        assertThat(t.getCreatedBy()).isEqualTo(99L);
        assertThat(t.getPrimaryLocale()).isEqualTo("ko-KR");
    }

    @Test
    void changeStatus_ACTIVE_to_SUSPENDED_허용() {
        Tenant t = Tenant.create("01H", "code", "name", "STANDARD", 1L);
        t.changeStatus(TenantStatus.SUSPENDED);
        assertThat(t.getStatus()).isEqualTo(TenantStatus.SUSPENDED);
    }

    @Test
    void changeStatus_to_CLOSED_는_금지() {
        Tenant t = Tenant.create("01H", "code", "name", "STANDARD", 1L);
        assertThatThrownBy(() -> t.changeStatus(TenantStatus.CLOSED))
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    void close_는_SUSPENDED_에서만_허용() {
        Tenant t = Tenant.create("01H", "code", "name", "STANDARD", 1L);
        assertThatThrownBy(() -> t.close(1L))
                .isInstanceOf(IllegalStateException.class);

        t.changeStatus(TenantStatus.SUSPENDED);
        t.close(1L);
        assertThat(t.getStatus()).isEqualTo(TenantStatus.CLOSED);
        assertThat(t.getDeletedAt()).isNotNull();
    }
}
