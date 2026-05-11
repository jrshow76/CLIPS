package com.tulip.tenant.config;

import com.tulip.tenant.outbox.RlsSessionApplier;
import com.tulip.tenant.security.TenantSessionContext;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.session.ResultHandler;
import org.apache.ibatis.session.RowBounds;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * RLS 세션 변수 자동 적용 MyBatis Interceptor.
 *
 * <p>모든 MyBatis 쿼리(update/query) 전에 현재 트랜잭션에 대해 1회만
 * {@code SET LOCAL app.current_tenant / app.role} 을 실행한다.
 *
 * 트랜잭션 동기화 자원으로 "이미 적용됨" 마커를 두어 중복 실행을 방지한다.</p>
 */
@Intercepts({
        @Signature(type = Executor.class, method = "update",
                args = {MappedStatement.class, Object.class}),
        @Signature(type = Executor.class, method = "query",
                args = {MappedStatement.class, Object.class, RowBounds.class, ResultHandler.class}),
        @Signature(type = Executor.class, method = "query",
                args = {MappedStatement.class, Object.class, RowBounds.class, ResultHandler.class,
                        org.apache.ibatis.cache.CacheKey.class,
                        org.apache.ibatis.mapping.BoundSql.class})
})
public class RlsMyBatisInterceptor implements Interceptor {

    private static final Logger log = LoggerFactory.getLogger(RlsMyBatisInterceptor.class);

    /** 트랜잭션 단위 적용 마커 키. */
    private static final String APPLIED_KEY = "tulip.tenant.rls.applied";

    private final ObjectProvider<RlsSessionApplier> applierProvider;

    public RlsMyBatisInterceptor(ObjectProvider<RlsSessionApplier> applierProvider) {
        this.applierProvider = applierProvider;
    }

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        applyIfNeeded();
        return invocation.proceed();
    }

    private void applyIfNeeded() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            return;
        }
        if (Boolean.TRUE.equals(TransactionSynchronizationManager.getResource(APPLIED_KEY))) {
            return;
        }
        TenantSessionContext.Holder h = TenantSessionContext.get();
        if (h == null) {
            return;
        }
        try {
            RlsSessionApplier applier = applierProvider.getIfAvailable();
            if (applier == null) {
                return;
            }
            if (h.bypass()) {
                applier.applySysAdmin();
            } else if (h.tenantId() != null) {
                applier.applyTenant(h.tenantId(), h.role());
            } else if ("SYS_ADMIN".equals(h.role())) {
                applier.applySysAdmin();
            }
            TransactionSynchronizationManager.bindResource(APPLIED_KEY, Boolean.TRUE);
            // 트랜잭션 종료 시 자동 unbind 되도록 동기화 등록
            TransactionSynchronizationManager.registerSynchronization(
                    new org.springframework.transaction.support.TransactionSynchronization() {
                        @Override
                        public void afterCompletion(int status) {
                            if (TransactionSynchronizationManager.hasResource(APPLIED_KEY)) {
                                TransactionSynchronizationManager.unbindResource(APPLIED_KEY);
                            }
                        }
                    }
            );
        } catch (Exception ex) {
            log.warn("RLS 적용 실패 (호출 진행) cause={}", ex.getMessage());
        }
    }
}
