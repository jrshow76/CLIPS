package com.tulip.common.tenant.context;

/**
 * 멀티테넌트 컨텍스트를 담는 불변 값 객체.
 *
 * <p>{@code tenantId} 는 절대 필수, {@code libraryId}/{@code userId}/{@code roles} 는 옵션이다.
 * 본 객체는 {@link TenantContextHolder} 가 ThreadLocal 에 보관한다.</p>
 *
 * @param tenantId   테넌트(조직) 식별자
 * @param libraryId  현재 활성 관(분관) 식별자
 * @param userId     인증 사용자(sub)
 * @param memberType STAFF/PATRON/DEVICE/PLATFORM_ADMIN
 * @param platformAdmin 플랫폼 관리자 여부 (X-Tenant-Id 임의 전환 가능)
 */
public record TenantContext(
        String tenantId,
        String libraryId,
        String userId,
        String memberType,
        boolean platformAdmin
) {

    /** 익명/비인증 컨텍스트(OPAC 등). */
    public static TenantContext anonymous(String tenantId) {
        return new TenantContext(tenantId, null, null, "ANONYMOUS", false);
    }

    /** tenantId 가 비어있는지 여부. */
    public boolean isEmpty() {
        return tenantId == null || tenantId.isBlank();
    }
}
