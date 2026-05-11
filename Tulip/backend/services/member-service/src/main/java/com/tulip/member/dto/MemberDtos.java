package com.tulip.member.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;

/**
 * 회원 도메인의 요청/응답 DTO 묶음.
 *
 * <p>모든 DTO 는 Java record 로 정의하며 camelCase 필드명을 사용한다 ({@code 03_api_standards.md} §4.4).</p>
 */
public final class MemberDtos {

    private MemberDtos() {
    }

    /** 회원 등록 요청. */
    public record CreateMemberRequest(
            @NotBlank @Size(max = 100) String name,
            @Size(max = 200) @Email String email,
            @Pattern(regexp = "^[0-9+\\-() ]{6,30}$", message = "전화번호 형식이 올바르지 않습니다") String phone,
            LocalDate birthdate,
            @NotBlank String memberTypeCode,
            Long libraryId,
            JsonNode address,
            List<ConsentInput> consents
    ) {
    }

    /** 회원 정보 부분 수정 요청 (PATCH). */
    public record UpdateMemberRequest(
            @Size(max = 100) String name,
            @Size(max = 200) @Email String email,
            @Pattern(regexp = "^[0-9+\\-() ]{6,30}$", message = "전화번호 형식이 올바르지 않습니다") String phone,
            LocalDate birthdate,
            String memberTypeCode,
            Long libraryId,
            JsonNode address,
            String status
    ) {
    }

    /** 회원 응답 (목록/상세 공용). */
    public record MemberResponse(
            Long id,
            String publicId,
            String memberNo,
            String name,
            String email,
            String phone,
            LocalDate birthdate,
            String memberTypeCode,
            String status,
            Long libraryId,
            JsonNode address,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt,
            OffsetDateTime suspendedAt
    ) {
    }

    /** 회원 검색 파라미터. */
    public record MemberSearchCriteria(
            String q,
            String status,
            Long libraryId,
            String memberTypeCode
    ) {
    }

    /** 회원증 발급 요청. */
    public record IssueCardRequest(
            @NotBlank String cardType,
            LocalDate expireDate,
            String issuedReason
    ) {
    }

    /** 회원증 상태/만료 변경 요청. */
    public record UpdateCardRequest(
            String status,
            LocalDate expireDate,
            String issuedReason
    ) {
    }

    /** 회원증 응답. */
    public record CardResponse(
            Long id,
            Long memberId,
            String cardNo,
            String cardType,
            String status,
            LocalDate issuedDate,
            LocalDate expireDate,
            String issuedReason,
            OffsetDateTime createdAt,
            OffsetDateTime updatedAt
    ) {
    }

    /** 동의 입력. */
    public record ConsentInput(
            @NotBlank String consentType,
            boolean granted,
            String version,
            String channel
    ) {
    }

    /** 동의 응답. */
    public record ConsentResponse(
            Long id,
            Long memberId,
            String consentType,
            boolean granted,
            String version,
            String channel,
            OffsetDateTime grantedAt,
            OffsetDateTime revokedAt
    ) {
    }
}
