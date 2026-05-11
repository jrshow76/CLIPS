package com.tulip.tenant.domain;

import java.time.OffsetDateTime;

/**
 * 테넌트 설정 KV. {@code key} 는 {@code NAMESPACE.KEY} 대문자 점-구분 형식이다.
 */
public class TenantSetting {

    private Long id;
    private Long tenantId;
    private String key;
    private String valueJson;
    private String description;
    private OffsetDateTime createdAt;
    private Long createdBy;
    private OffsetDateTime updatedAt;
    private Long updatedBy;
    private OffsetDateTime deletedAt;
    private int version;

    public TenantSetting() {
    }

    public static TenantSetting of(Long tenantId, String key, String valueJson, String description, Long updatedBy) {
        TenantSetting s = new TenantSetting();
        s.tenantId = tenantId;
        s.key = key;
        s.valueJson = valueJson == null ? "{}" : valueJson;
        s.description = description;
        s.createdBy = updatedBy;
        s.updatedBy = updatedBy;
        return s;
    }

    /** value 값 갱신. */
    public void changeValue(String valueJson, Long updatedBy) {
        this.valueJson = valueJson == null ? "{}" : valueJson;
        this.updatedBy = updatedBy;
    }

    // ---------- getter / setter ----------
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }
    public String getValueJson() { return valueJson; }
    public void setValueJson(String valueJson) { this.valueJson = valueJson; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
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
