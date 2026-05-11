package com.tulip.common.tenant.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 호출 시점에 유효한 {@code TenantContext} 가 반드시 존재해야 함을 명시한다.
 *
 * <p>AOP 또는 인터셉터가 본 어노테이션을 감지하여 누락 시 403 으로 차단한다.
 * 플랫폼 관리자 API 등 일부 메서드는 본 어노테이션을 부착하지 않을 수 있다.</p>
 */
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
public @interface RequiresTenant {

    /** 플랫폼 관리자의 컨텍스트 우회를 허용할지 여부. 기본 false. */
    boolean allowPlatformAdmin() default false;
}
