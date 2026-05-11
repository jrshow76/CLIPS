package com.tulip.codepolicy.domain;

import java.time.OffsetDateTime;

/**
 * 정책 할당 엔티티 (pol_policy_assignment 매핑).
 *
 * <p>{@code targetType} 은 LIBRARY/MEMBER_TYPE/MATERIAL_TYPE/GLOBAL,
 * {@code targetId} 는 해당 타입의 외부 키 값.</p>
 */
public class PolicyAssignment {

    private Long id;
    private Long tenantId;
    private Long policyId;
    private String targetType;
    private String targetId;
    private Integer priority;
    private OffsetDateTime createdAt;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public Long getPolicyId() { return policyId; }
    public void setPolicyId(Long policyId) { this.policyId = policyId; }
    public String getTargetType() { return targetType; }
    public void setTargetType(String targetType) { this.targetType = targetType; }
    public String getTargetId() { return targetId; }
    public void setTargetId(String targetId) { this.targetId = targetId; }
    public Integer getPriority() { return priority; }
    public void setPriority(Integer priority) { this.priority = priority; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
