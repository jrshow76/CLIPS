package com.tulip.tenant.api.dto;

import com.tulip.tenant.domain.Tenant;
import com.tulip.tenant.domain.TenantStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.OffsetDateTime;

/**
 * Tenant 도메인 API 입출력 DTO 모음 (record).
 *
 * <p>외부 노출은 {@code publicId} (ULID) 우선이며, 내부 식별자(BIGINT id) 도
 * 운영성 편의를 위해 {@link Response} 에 함께 노출한다.</p>
 */
public final class TenantDtos {

    private TenantDtos() {
    }

    /** 테넌트 생성 요청. */
    public record CreateRequest(
            @NotBlank @Pattern(regexp = "^[a-z0-9][a-z0-9-]{1,62}$") String code,
            @NotBlank @Size(max = 255) String name,
            @Size(max = 32) String plan,
            String contactJson
    ) {
    }

    /** 테넌트 수정 요청 (PATCH — 모두 nullable). */
    public record UpdateRequest(
            @Size(max = 255) String name,
            String status,
            @Size(max = 32) String plan,
            String contactJson,
            String primaryLocale,
            String primaryTimezone
    ) {
    }

    /** 응답 DTO. */
    public record Response(
            Long id,
            String publicId,
            String code,
            String name,
            TenantStatus status,
            String plan,
            String primaryLocale,
            String primaryTimezone,
            String contactJson,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt,
            int version
    ) {
        public static Response from(Tenant t) {
            return new Response(
                    t.getId(), t.getPublicId(), t.getCode(), t.getName(),
                    t.getStatus(), t.getPlan(),
                    t.getPrimaryLocale(), t.getPrimaryTimezone(),
                    t.getContactJson(),
                    t.getCreatedAt(), t.getUpdatedAt(), t.getVersion()
            );
        }
    }

    /** 검색 조건. */
    public record SearchCondition(String code, String name, String status, int offset, int limit) {
    }
}
