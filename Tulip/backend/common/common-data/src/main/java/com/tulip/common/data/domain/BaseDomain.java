package com.tulip.common.data.domain;

import java.time.OffsetDateTime;

/**
 * 모든 도메인 객체의 공통 audit/소프트삭제/낙관락 필드를 노출하는 추상 클래스.
 *
 * <p>대응 DB 컬럼: {@code created_at, created_by, updated_at, updated_by, deleted_at, version}.
 * 정의는 {@code 10_dba/01_data_modeling_principles.md} §6 의 공통 컬럼 표준을 따른다.</p>
 *
 * <p>구현체는 도메인 객체 자체가 본 추상 클래스를 상속하거나, 또는 컴포지션으로
 * {@link AuditingFields} 를 보유하는 방식 중 선택할 수 있다.</p>
 */
public abstract class BaseDomain {

    private Long id;
    private Long tenantId;
    private Long libraryId;
    private AuditingFields auditing = new AuditingFields();

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getTenantId() {
        return tenantId;
    }

    public void setTenantId(Long tenantId) {
        this.tenantId = tenantId;
    }

    public Long getLibraryId() {
        return libraryId;
    }

    public void setLibraryId(Long libraryId) {
        this.libraryId = libraryId;
    }

    public AuditingFields getAuditing() {
        return auditing;
    }

    public void setAuditing(AuditingFields auditing) {
        this.auditing = auditing;
    }

    /** 소프트 삭제된 행 여부. */
    public boolean isDeleted() {
        return auditing != null && auditing.getDeletedAt() != null;
    }

    /** 소프트 삭제를 적용한다. */
    public void markDeleted(Long deletedBy) {
        if (auditing == null) {
            auditing = new AuditingFields();
        }
        auditing.setDeletedAt(OffsetDateTime.now());
        auditing.setUpdatedBy(deletedBy);
    }
}
