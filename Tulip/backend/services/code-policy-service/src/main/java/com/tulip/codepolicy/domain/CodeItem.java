package com.tulip.codepolicy.domain;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.OffsetDateTime;

/**
 * 코드 값 엔티티 (cd_code 매핑).
 *
 * <p>코드 그룹에 속하며, 계층 구조가 필요한 그룹은 {@code parentId} 로 트리를 형성한다.
 * 추가 속성은 {@code attributesJson} 으로 저장한다 (JSONB).</p>
 */
public class CodeItem {

    private Long id;
    private Long tenantId;
    private Long groupId;
    private String groupCode;
    private String code;
    private String name;
    private String description;
    private Long parentId;
    private Integer sortOrder;
    private boolean active;
    private JsonNode attributesJson;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
    private Integer version;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public Long getGroupId() { return groupId; }
    public void setGroupId(Long groupId) { this.groupId = groupId; }
    public String getGroupCode() { return groupCode; }
    public void setGroupCode(String groupCode) { this.groupCode = groupCode; }
    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public Long getParentId() { return parentId; }
    public void setParentId(Long parentId) { this.parentId = parentId; }
    public Integer getSortOrder() { return sortOrder; }
    public void setSortOrder(Integer sortOrder) { this.sortOrder = sortOrder; }
    public boolean isActive() { return active; }
    public void setActive(boolean active) { this.active = active; }
    public JsonNode getAttributesJson() { return attributesJson; }
    public void setAttributesJson(JsonNode attributesJson) { this.attributesJson = attributesJson; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(OffsetDateTime updatedAt) { this.updatedAt = updatedAt; }
    public Integer getVersion() { return version; }
    public void setVersion(Integer version) { this.version = version; }
}
