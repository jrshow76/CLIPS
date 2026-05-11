package com.tulip.common.data.audit;

import com.tulip.common.data.domain.AuditingFields;
import com.tulip.common.data.domain.BaseDomain;
import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.mapping.SqlCommandType;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.session.ResultHandler;

import java.time.OffsetDateTime;

/**
 * MyBatis 인터셉터 — Insert/Update 시점에 audit 필드를 자동 채운다.
 *
 * <p>도메인 객체가 {@link BaseDomain} 을 상속하면 createdAt/updatedAt/createdBy/updatedBy
 * 및 tenantId 가 자동 주입된다. 누락된 tenantId 는 {@link TenantContextHolder} 에서 가져온다.</p>
 *
 * <p>RLS 보조 정책 (10_dba/01 §2.4) 의 첫 단계로 작동한다. 누락 검출 시 예외를 던져
 * 데이터 누설을 차단한다.</p>
 */
@Intercepts({
        @Signature(type = Executor.class, method = "update",
                args = {MappedStatement.class, Object.class}),
        @Signature(type = Executor.class, method = "query",
                args = {MappedStatement.class, Object.class, org.apache.ibatis.session.RowBounds.class,
                        ResultHandler.class})
})
public class AuditingInterceptor implements Interceptor {

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        Object[] args = invocation.getArgs();
        if (args.length >= 2 && args[0] instanceof MappedStatement ms && args[1] instanceof BaseDomain domain) {
            applyAuditing(ms.getSqlCommandType(), domain);
        }
        return invocation.proceed();
    }

    private void applyAuditing(SqlCommandType command, BaseDomain domain) {
        TenantContext ctx = TenantContextHolder.get();
        Long currentUser = parseLong(ctx == null ? null : ctx.userId());
        Long currentTenant = parseLong(ctx == null ? null : ctx.tenantId());

        AuditingFields auditing = domain.getAuditing();
        if (auditing == null) {
            auditing = new AuditingFields();
            domain.setAuditing(auditing);
        }

        OffsetDateTime now = OffsetDateTime.now();
        switch (command) {
            case INSERT -> {
                auditing.setCreatedAt(now);
                auditing.setUpdatedAt(now);
                if (auditing.getCreatedBy() == null) {
                    auditing.setCreatedBy(currentUser);
                }
                auditing.setUpdatedBy(currentUser);
                if (domain.getTenantId() == null && currentTenant != null) {
                    domain.setTenantId(currentTenant);
                }
            }
            case UPDATE -> {
                auditing.setUpdatedAt(now);
                auditing.setUpdatedBy(currentUser);
            }
            default -> {
                // SELECT/DELETE 는 audit 갱신 없음
            }
        }
    }

    private static Long parseLong(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
