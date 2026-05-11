package com.tulip.common.data.rls;

import com.tulip.common.tenant.context.TenantContext;
import com.tulip.common.tenant.context.TenantContextHolder;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;

/**
 * PostgreSQL Row Level Security 적용을 위한 세션 변수 헬퍼.
 *
 * <p>JDBC 커넥션 획득 직후 {@code SET LOCAL app.current_tenant = ?} 를 실행하면
 * RLS 정책 {@code tenant_id = current_setting('app.current_tenant')::BIGINT} 가 자동 적용된다.
 * (10_dba/01 §2.4 RLS 정책 참조)</p>
 *
 * <p>운영에서는 본 헬퍼 호출이 DataSource 의 ConnectionAcquireListener 또는
 * MyBatis 인터셉터로 자동화된다. Phase 1-A 는 헬퍼만 제공한다.</p>
 */
public final class RlsContextHelper {

    public static final String SETTING_TENANT = "app.current_tenant";
    public static final String SETTING_LIBRARY = "app.current_library";
    public static final String SETTING_USER = "app.current_user";

    private RlsContextHelper() {
    }

    /** 트랜잭션 범위로 RLS 세션 변수를 설정한다. */
    public static void applyToConnection(Connection conn, TenantContext context) throws SQLException {
        if (conn == null || context == null) {
            return;
        }
        executeSet(conn, SETTING_TENANT, context.tenantId());
        executeSet(conn, SETTING_LIBRARY, context.libraryId());
        executeSet(conn, SETTING_USER, context.userId());
    }

    /** ThreadLocal 의 컨텍스트를 사용하는 편의 메서드. */
    public static void applyCurrent(DataSource dataSource) throws SQLException {
        TenantContext ctx = TenantContextHolder.get();
        if (ctx == null) {
            return;
        }
        try (Connection conn = dataSource.getConnection()) {
            applyToConnection(conn, ctx);
        }
    }

    private static void executeSet(Connection conn, String key, String value) throws SQLException {
        if (value == null || value.isBlank()) {
            return;
        }
        // SET LOCAL 은 prepared statement 가 아닌 단순 문장으로 실행해야 한다.
        // key 는 화이트리스트만 사용 — SQL Injection 차단 (06_coding_standards §10).
        if (!isAllowedKey(key)) {
            throw new SQLException("허용되지 않은 RLS 키: " + key);
        }
        try (PreparedStatement ps = conn.prepareStatement("SELECT set_config(?, ?, true)")) {
            ps.setString(1, key);
            ps.setString(2, value);
            ps.execute();
        }
    }

    private static boolean isAllowedKey(String key) {
        return SETTING_TENANT.equals(key) || SETTING_LIBRARY.equals(key) || SETTING_USER.equals(key);
    }
}
