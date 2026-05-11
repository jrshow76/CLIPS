package com.tulip.tenant.api.dto;

import com.tulip.tenant.domain.TenantSetting;
import jakarta.validation.constraints.NotBlank;

import java.time.OffsetDateTime;

/**
 * 테넌트 설정 API DTO.
 */
public final class TenantSettingDtos {

    private TenantSettingDtos() {
    }

    public record UpsertRequest(
            @NotBlank String valueJson,
            String description
    ) {
    }

    public record Response(
            Long id,
            Long tenantId,
            String key,
            String valueJson,
            String description,
            OffsetDateTime updatedAt
    ) {
        public static Response from(TenantSetting s) {
            return new Response(
                    s.getId(), s.getTenantId(), s.getKey(),
                    s.getValueJson(), s.getDescription(),
                    s.getUpdatedAt()
            );
        }
    }
}
