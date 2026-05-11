package com.tulip.common.web.config;

import com.tulip.common.tenant.filter.TenantContextFilter;
import com.tulip.common.web.advice.GlobalExceptionHandler;
import com.tulip.common.web.filter.RequestLoggingFilter;
import com.tulip.common.web.filter.TraceIdFilter;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * common-web 모듈의 Spring Boot AutoConfiguration.
 *
 * <p>각 서비스가 본 모듈을 의존성에 추가하기만 하면 traceId/tenant/접근로그 필터와
 * 전역 예외 핸들러, OpenAPI 설정이 자동 등록된다.</p>
 */
@AutoConfiguration
@ConditionalOnClass(OncePerRequestFilter.class)
@Import({GlobalExceptionHandler.class, OpenApiConfig.class})
public class CommonWebAutoConfiguration {

    @Bean
    public FilterRegistrationBean<TraceIdFilter> traceIdFilter() {
        FilterRegistrationBean<TraceIdFilter> bean = new FilterRegistrationBean<>(new TraceIdFilter());
        bean.setOrder(bean.getFilter().getOrder());
        return bean;
    }

    @Bean
    public FilterRegistrationBean<TenantContextFilter> tenantContextFilter() {
        FilterRegistrationBean<TenantContextFilter> bean = new FilterRegistrationBean<>(new TenantContextFilter());
        bean.setOrder(bean.getFilter().getOrder());
        return bean;
    }

    @Bean
    public FilterRegistrationBean<RequestLoggingFilter> requestLoggingFilter() {
        FilterRegistrationBean<RequestLoggingFilter> bean = new FilterRegistrationBean<>(new RequestLoggingFilter());
        bean.setOrder(bean.getFilter().getOrder());
        return bean;
    }
}
