package com.tulip.tenant.domain;

import java.time.OffsetDateTime;

/**
 * 분관(Branch) 도메인 — 라이브러리 하위 운영/소장 단위.
 *
 * <p>DBA 스키마상 tenant_id 를 같이 보유한다 (RLS 단순화 목적).</p>
 */
public class LibraryBranch {

    private Long id;
    private String publicId;
    private Long tenantId;
    private Long libraryId;
    private String code;
    private String name;
    private TenantStatus status;
    private String addressJson;
    private String contactJson;
    private OffsetDateTime createdAt;
    private Long createdBy;
    private OffsetDateTime updatedAt;
    private Long updatedBy;
    private OffsetDateTime deletedAt;
    private int version;

    public LibraryBranch() {
    }

    public static LibraryBranch create(String publicId, Long tenantId, Long libraryId,
                                       String code, String name, Long createdBy) {
        LibraryBranch b = new LibraryBranch();
        b.publicId = publicId;
        b.tenantId = tenantId;
        b.libraryId = libraryId;
        b.code = code;
        b.name = name;
        b.status = TenantStatus.ACTIVE;
        b.addressJson = "{}";
        b.contactJson = "{}";
        b.createdBy = createdBy;
        b.updatedBy = createdBy;
        return b;
    }

    public void softDelete(Long deletedBy) {
        this.status = TenantStatus.CLOSED;
        this.deletedAt = OffsetDateTime.now();
        this.updatedBy = deletedBy;
    }

    // ---------- getter / setter ----------
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getPublicId() { return publicId; }
    public void setPublicId(String publicId) { this.publicId = publicId; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public Long getLibraryId() { return libraryId; }
    public void setLibraryId(Long libraryId) { this.libraryId = libraryId; }
    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public TenantStatus getStatus() { return status; }
    public void setStatus(TenantStatus status) { this.status = status; }
    public String getAddressJson() { return addressJson; }
    public void setAddressJson(String addressJson) { this.addressJson = addressJson; }
    public String getContactJson() { return contactJson; }
    public void setContactJson(String contactJson) { this.contactJson = contactJson; }
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
    public int getVersion() { return version; }
    public void setVersion(int version) { this.version = version; }
}
