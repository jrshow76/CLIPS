package com.tulip.tenant.security;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 시스템 관리자 컨텍스트(테넌트 격리 우회) 모드 진입을 명시하는 마커 어노테이션.
 *
 * <p>본 단계(1-C)에서는 어노테이션 인식만 마련하며, 실제 우회는
 * "SYS_ADMIN 토큰 + X-Sys-Bypass: true" 조합이 들어왔을 때 허용된다.
 * 자세한 동작은 {@link TenantAuthFilter} 참고.</p>
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
public @interface SystemAdmin {
}
