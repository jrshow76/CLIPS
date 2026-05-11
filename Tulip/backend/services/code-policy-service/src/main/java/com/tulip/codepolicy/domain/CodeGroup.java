package com.tulip.codepolicy.domain;

import java.time.OffsetDateTime;

/**
 * 코드 그룹 엔티티 (cd_code_group 매핑).
 *
 * <p>{@code tenantId} 가 NULL 이면 글로벌 코드 그룹, NOT NULL 이면 테넌트 한정.</p>
 */
public class CodeGroup {

    private Long id;
    private Long tenantId;
    private String groupCode;
    private String groupName;
    private String description;
    private boolean editable;
    private boolean hierarchical;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private Integer version;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public String getGroupCode() { return groupCode; }
    public void setGroupCode(String groupCode) { this.groupCode = groupCode; }
    public String getGroupName() { return groupName; }
    public void setGroupName(String groupName) { this.groupName = groupName; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public boolean isEditable() { return editable; }
    public void setEditable(boolean editable) { this.editable = editable; }
    public boolean isHierarchical() { return hierarchical; }
    public void setHierarchical(boolean hierarchical) { this.hierarchical = hierarchical; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
    public Integer getVersion() { return version; }
    public void setVersion(Integer version) { this.version = version; }

    public boolean isGlobal() { return tenantId == null; }
}
