package com.tulip.codepolicy.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * 정책 도메인 요청/응답 DTO.
 */
public final class PolicyDtos {

    private PolicyDtos() {
    }

    public record PolicyResponse(
            Long id,
            Long tenantId,
            String policyCode,
            String name,
            String description,
            String policyVersion,
            JsonNode rules,
            LocalDate effectiveFrom,
            LocalDate effectiveTo,
            boolean active,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt,
            List<AssignmentResponse> assignments
    ) {
    }

    public record AssignmentResponse(
            Long id,
            Long policyId,
            String targetType,
            String targetId,
            Integer priority
    ) {
    }

    public record CreatePolicyRequest(
            @NotBlank @Size(max = 64) String policyCode,
            @NotBlank @Size(max = 200) String name,
            String description,
            String policyVersion,
            @NotNull JsonNode rules,
            LocalDate effectiveFrom,
            LocalDate effectiveTo,
            Boolean active
    ) {
    }

    public record UpdatePolicyRequest(
            @Size(max = 200) String name,
            String description,
            String policyVersion,
            JsonNode rules,
            LocalDate effectiveFrom,
            LocalDate effectiveTo,
            Boolean active
    ) {
    }

    public record AssignmentInput(
            @NotBlank String targetType,
            @NotBlank String targetId,
            Integer priority
    ) {
    }

    public record AssignmentsRequest(
            @NotNull List<AssignmentInput> assignments
    ) {
    }

    public record EffectivePolicyResponse(
            Long policyId,
            String policyCode,
            String name,
            String policyVersion,
            JsonNode rules,
            String matchedTargetType,
            String matchedTargetId,
            Integer matchedPriority
    ) {
    }
}
