package com.tulip.codepolicy.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * 코드 도메인 요청/응답 DTO.
 */
public final class CodeDtos {

    private CodeDtos() {
    }

    public record CodeGroupResponse(
            Long id,
            Long tenantId,
            String groupCode,
            String groupName,
            String description,
            boolean editable,
            boolean hierarchical,
            boolean global
    ) {
    }

    public record CodeItemResponse(
            Long id,
            Long tenantId,
            String groupCode,
            String code,
            String name,
            String description,
            Long parentId,
            Integer sortOrder,
            boolean active,
            JsonNode attributes,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt,
            List<CodeItemResponse> children
    ) {
    }

    public record CreateCodeItemRequest(
            @NotBlank @Size(max = 64) String code,
            @NotBlank @Size(max = 200) String name,
            String description,
            Long parentId,
            Integer sortOrder,
            Boolean active,
            JsonNode attributes
    ) {
    }

    public record UpdateCodeItemRequest(
            @Size(max = 200) String name,
            String description,
            Long parentId,
            Integer sortOrder,
            Boolean active,
            JsonNode attributes
    ) {
    }
}
