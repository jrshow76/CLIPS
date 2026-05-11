package com.tulip.tenant.api.dto;

import com.tulip.tenant.domain.Library;
import com.tulip.tenant.domain.LibraryBranch;
import com.tulip.tenant.domain.LibraryType;
import com.tulip.tenant.domain.TenantStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.OffsetDateTime;

/**
 * 라이브러리·분관 API DTO 묶음.
 */
public final class LibraryDtos {

    private LibraryDtos() {
    }

    public record CreateRequest(
            @NotBlank @Pattern(regexp = "^[a-z0-9][a-z0-9-]{1,62}$") String code,
            @NotBlank @Size(max = 255) String name,
            String type,
            String addressJson,
            String contactJson,
            String openingHoursJson
    ) {
    }

    public record UpdateRequest(
            @Size(max = 255) String name,
            String status,
            String addressJson,
            String contactJson,
            String openingHoursJson
    ) {
    }

    public record Response(
            Long id,
            String publicId,
            Long tenantId,
            String code,
            String name,
            LibraryType type,
            TenantStatus status,
            String addressJson,
            String contactJson,
            String openingHoursJson,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt,
            int version
    ) {
        public static Response from(Library l) {
            return new Response(
                    l.getId(), l.getPublicId(), l.getTenantId(), l.getCode(), l.getName(),
                    l.getType(), l.getStatus(),
                    l.getAddressJson(), l.getContactJson(), l.getOpeningHoursJson(),
                    l.getCreatedAt(), l.getUpdatedAt(), l.getVersion()
            );
        }
    }

    public record SearchCondition(String name, String status, int offset, int limit) {
    }

    public record BranchCreateRequest(
            @NotBlank @Pattern(regexp = "^[a-z0-9][a-z0-9-]{1,62}$") String code,
            @NotBlank @Size(max = 255) String name,
            String addressJson,
            String contactJson
    ) {
    }

    public record BranchUpdateRequest(
            @Size(max = 255) String name,
            String status,
            String addressJson,
            String contactJson
    ) {
    }

    public record BranchResponse(
            Long id,
            String publicId,
            Long tenantId,
            Long libraryId,
            String code,
            String name,
            TenantStatus status,
            String addressJson,
            String contactJson,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt,
            int version
    ) {
        public static BranchResponse from(LibraryBranch b) {
            return new BranchResponse(
                    b.getId(), b.getPublicId(), b.getTenantId(), b.getLibraryId(),
                    b.getCode(), b.getName(), b.getStatus(),
                    b.getAddressJson(), b.getContactJson(),
                    b.getCreatedAt(), b.getUpdatedAt(), b.getVersion()
            );
        }
    }
}
