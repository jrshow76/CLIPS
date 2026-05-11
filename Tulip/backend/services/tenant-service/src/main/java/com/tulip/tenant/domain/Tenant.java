package com.tulip.tenant.domain;

import java.time.OffsetDateTime;

/**
 * 테넌트(고객 도서관 조직) 도메인 객체.
 *
 * <p>SYS_ADMIN 만이 본 도메인을 직접 다루며, 일반 테넌트 관리자는
 * 자신이 속한 테넌트만 read/update 한다. RLS 정책 {@code pol_tnt_tenant_*}
 * 는 {@code app.role = 'SYS_ADMIN'} 조건으로 access 를 제한한다.</p>
 *
 * <p>본 객체는 MyBatis ResultMap 으로 매핑되므로 가변(setter) 도메인이지만,
 * 비즈니스 규칙 메서드를 통해서만 상태가 바뀌도록 가급적 캡슐화한다.</p>
 */
public class Tenant {

    private Long id;
    private String publicId;
    private String code;
    private String name;
    private TenantStatus status;
    private String plan;
    private String primaryLocale;
    private String primaryTimezone;
    private String contactJson;
    private OffsetDateTime createdAt;
    private Long createdBy;
    private OffsetDateTime updatedAt;
    private Long updatedBy;
    private OffsetDateTime deletedAt;
    private int version;

    public Tenant() {
    }

    /** 신규 생성 정적 팩토리. */
    public static Tenant create(String publicId, String code, String name, String plan, Long createdBy) {
        Tenant t = new Tenant();
        t.publicId = publicId;
        t.code = code;
        t.name = name;
        t.status = TenantStatus.ACTIVE;
        t.plan = plan == null ? "STANDARD" : plan;
        t.primaryLocale = "ko-KR";
        t.primaryTimezone = "Asia/Seoul";
        t.contactJson = "{}";
        t.createdBy = createdBy;
        t.updatedBy = createdBy;
        return t;
    }

    // ---------- 비즈니스 규칙 ----------

    /** 상태 전이: ACTIVE <-> SUSPENDED. CLOSED 는 별도 메서드. */
    public void changeStatus(TenantStatus next) {
        if (next == null) {
            throw new IllegalArgumentException("status 는 null 일 수 없습니다");
        }
        if (this.status == TenantStatus.CLOSED) {
            throw new IllegalStateException("CLOSED 상태에서는 상태 전이가 불가합니다");
        }
        if (next == TenantStatus.CLOSED) {
            throw new IllegalStateException("CLOSED 로의 전이는 close() 를 통해 수행하세요");
        }
        this.status = next;
    }

    /** 종료(소프트 삭제). SUSPENDED 상태에서만 허용. */
    public void close(Long deletedBy) {
        if (this.status != TenantStatus.SUSPENDED) {
            throw new IllegalStateException("SUSPENDED 상태에서만 종료할 수 있습니다");
        }
        this.status = TenantStatus.CLOSED;
        this.deletedAt = OffsetDateTime.now();
        this.updatedBy = deletedBy;
    }

    /** 플랜 변경. */
    public void changePlan(String plan) {
        if (plan == null || plan.isBlank()) {
            throw new IllegalArgumentException("plan 은 비어있을 수 없습니다");
        }
        this.plan = plan;
    }

    // ---------- getter / setter ----------
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getPublicId() { return publicId; }
    public void setPublicId(String publicId) { this.publicId = publicId; }
    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public TenantStatus getStatus() { return status; }
    public void setStatus(TenantStatus status) { this.status = status; }
    public String getPlan() { return plan; }
    public void setPlan(String plan) { this.plan = plan; }
    public String getPrimaryLocale() { return primaryLocale; }
    public void setPrimaryLocale(String primaryLocale) { this.primaryLocale = primaryLocale; }
    public String getPrimaryTimezone() { return primaryTimezone; }
    public void setPrimaryTimezone(String primaryTimezone) { this.primaryTimezone = primaryTimezone; }
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
