package com.tulip.tenant.domain;

import java.time.OffsetDateTime;

/**
 * 도서관(라이브러리) 도메인 — 테넌트 내 운영 단위.
 *
 * <p>RLS 정책으로 {@code tenant_id = current_setting('app.current_tenant')::BIGINT}
 * 가 자동 적용되어 테넌트 간 격리가 보장된다.</p>
 */
public class Library {

    private Long id;
    private String publicId;
    private Long tenantId;
    private String code;
    private String name;
    private LibraryType type;
    private TenantStatus status;
    private String addressJson;
    private String contactJson;
    private String openingHoursJson;
    private OffsetDateTime createdAt;
    private Long createdBy;
    private OffsetDateTime updatedAt;
    private Long updatedBy;
    private OffsetDateTime deletedAt;
    private int version;

    public Library() {
    }

    public static Library create(String publicId, Long tenantId, String code, String name,
                                 LibraryType type, Long createdBy) {
        Library lib = new Library();
        lib.publicId = publicId;
        lib.tenantId = tenantId;
        lib.code = code;
        lib.name = name;
        lib.type = type == null ? LibraryType.CENTRAL : type;
        lib.status = TenantStatus.ACTIVE;
        lib.addressJson = "{}";
        lib.contactJson = "{}";
        lib.openingHoursJson = "{}";
        lib.createdBy = createdBy;
        lib.updatedBy = createdBy;
        return lib;
    }

    public void changeStatus(TenantStatus next) {
        if (next == null) {
            throw new IllegalArgumentException("status null");
        }
        if (this.status == TenantStatus.CLOSED && next != TenantStatus.CLOSED) {
            throw new IllegalStateException("CLOSED 상태에서는 전이가 불가합니다");
        }
        this.status = next;
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
    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public LibraryType getType() { return type; }
    public void setType(LibraryType type) { this.type = type; }
    public TenantStatus getStatus() { return status; }
    public void setStatus(TenantStatus status) { this.status = status; }
    public String getAddressJson() { return addressJson; }
    public void setAddressJson(String addressJson) { this.addressJson = addressJson; }
    public String getContactJson() { return contactJson; }
    public void setContactJson(String contactJson) { this.contactJson = contactJson; }
    public String getOpeningHoursJson() { return openingHoursJson; }
    public void setOpeningHoursJson(String openingHoursJson) { this.openingHoursJson = openingHoursJson; }
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
