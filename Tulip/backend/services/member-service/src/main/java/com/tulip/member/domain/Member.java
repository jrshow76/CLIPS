package com.tulip.member.domain;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.LocalDate;
import java.time.OffsetDateTime;

/**
 * 회원 도메인 엔티티 (mbr_member 매핑).
 *
 * <p>RLS 정책 {@code tenant_id = current_setting('app.current_tenant')::bigint} 가 자동 적용된다.
 * phone/address 는 pgcrypto 로 암호화되어 저장되나, 본 도메인 객체는 평문(혹은 마스킹된 표시값)을
 * 보관한다. 매퍼 레이어에서 암복호화·정규화(name_normalized/phone_normalized/email_lower)
 * 컬럼을 함께 처리한다.</p>
 */
public class Member {

    private Long id;
    private Long tenantId;
    private Long libraryId;
    private String publicId;
    private String memberNo;
    private String name;
    private String nameNormalized;
    private String email;
    private String emailLower;
    private String phone;
    private String phoneNormalized;
    private LocalDate birthdate;
    private String memberTypeCode;
    private String status;
    private JsonNode addressJson;
    private OffsetDateTime suspendedAt;
    private String suspendedReason;
    private OffsetDateTime createdAt;
    private Long createdBy;
    private OffsetDateTime updatedAt;
    private Long updatedBy;
    private OffsetDateTime deletedAt;
    private Integer version;

    public Member() {
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public Long getLibraryId() { return libraryId; }
    public void setLibraryId(Long libraryId) { this.libraryId = libraryId; }
    public String getPublicId() { return publicId; }
    public void setPublicId(String publicId) { this.publicId = publicId; }
    public String getMemberNo() { return memberNo; }
    public void setMemberNo(String memberNo) { this.memberNo = memberNo; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getNameNormalized() { return nameNormalized; }
    public void setNameNormalized(String nameNormalized) { this.nameNormalized = nameNormalized; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getEmailLower() { return emailLower; }
    public void setEmailLower(String emailLower) { this.emailLower = emailLower; }
    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }
    public String getPhoneNormalized() { return phoneNormalized; }
    public void setPhoneNormalized(String phoneNormalized) { this.phoneNormalized = phoneNormalized; }
    public LocalDate getBirthdate() { return birthdate; }
    public void setBirthdate(LocalDate birthdate) { this.birthdate = birthdate; }
    public String getMemberTypeCode() { return memberTypeCode; }
    public void setMemberTypeCode(String memberTypeCode) { this.memberTypeCode = memberTypeCode; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public JsonNode getAddressJson() { return addressJson; }
    public void setAddressJson(JsonNode addressJson) { this.addressJson = addressJson; }
    public OffsetDateTime getSuspendedAt() { return suspendedAt; }
    public void setSuspendedAt(OffsetDateTime suspendedAt) { this.suspendedAt = suspendedAt; }
    public String getSuspendedReason() { return suspendedReason; }
    public void setSuspendedReason(String suspendedReason) { this.suspendedReason = suspendedReason; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public Long getCreatedBy() { return createdBy; }
    public void setCreatedBy(Long createdBy) { this.createdBy = createdBy; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
    public Long getUpdatedBy() { return updatedBy; }
    public void setUpdatedBy(Long updatedBy) { this.updatedBy = updatedBy; }
    public OffsetDateTime getDeletedAt() { return deletedAt; }
    public void setDeletedAt(OffsetDateTime deletedAt) { this.deletedAt = deletedAt; }
    public Integer getVersion() { return version; }
    public void setVersion(Integer version) { this.version = version; }

    /** 활성 상태 여부. */
    public boolean isActive() {
        return "ACTIVE".equalsIgnoreCase(status) && deletedAt == null;
    }

    /** 정지 상태 여부. */
    public boolean isSuspended() {
        return "SUSPENDED".equalsIgnoreCase(status);
    }
}
