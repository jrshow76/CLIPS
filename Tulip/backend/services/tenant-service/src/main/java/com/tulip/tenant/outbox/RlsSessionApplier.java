package com.tulip.tenant.outbox;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/**
 * 트랜잭션 내부에서 RLS 세션 변수를 강제 적용하는 헬퍼.
 *
 * <p>Outbox Poller 같은 백그라운드 컴포넌트는 HTTP 요청 컨텍스트가 없어
 * 일반 RLS Interceptor 로는 SYS_ADMIN 컨텍스트를 부여할 수 없다.
 * 본 클래스가 그 갭을 채운다.</p>
 *
 * <p>호출은 반드시 활성 트랜잭션 내부에서 이루어져야 한다 ({@code SET LOCAL} 사용).</p>
 */
@Component
public class RlsSessionApplier {

    private static final Logger log = LoggerFactory.getLogger(RlsSessionApplier.class);

    private final JdbcTemplate jdbcTemplate;

    public RlsSessionApplier(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** SYS_ADMIN 컨텍스트로 세팅 (테넌트 격리 우회 — outbox 운영용). */
    public void applySysAdmin() {
        jdbcTemplate.queryForObject("SELECT set_config('app.role', ?, true)", String.class, "SYS_ADMIN");
        // 명시적으로 current_tenant 는 비워둔다 — outbox 는 tenant_id 가 NULL 인 row 도 다룸
        jdbcTemplate.queryForObject("SELECT set_config('app.current_tenant', '', true)", String.class);
    }

    /** 특정 테넌트 컨텍스트로 세팅. */
    public void applyTenant(Long tenantId, String role) {
        if (tenantId != null) {
            jdbcTemplate.queryForObject("SELECT set_config('app.current_tenant', ?, true)",
                    String.class, tenantId.toString());
        }
        jdbcTemplate.queryForObject("SELECT set_config('app.role', ?, true)",
                String.class, role == null ? "TENANT_ADMIN" : role);
        log.trace("RLS applied tenantId={} role={}", tenantId, role);
    }
}
