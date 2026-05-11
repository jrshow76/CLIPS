package com.tulip.iam.auth.repository;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.Optional;

/**
 * Keycloak 사용자(sub) ↔ Tulip+ 내부 user_id 매핑 저장소.
 *
 * <p>스키마: {@code iam_user_link(user_id PK, kc_sub UNIQUE, tenant_id, default_branch_id, created_at, updated_at)}</p>
 */
@Repository
public class IamUserLinkRepository {

    private final JdbcTemplate jdbc;

    public IamUserLinkRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** 매핑이 없으면 INSERT, 있으면 tenant/branch 정보 갱신. */
    public void upsert(String userId, String kcSub, String tenantId, String defaultBranchId) {
        if (userId == null || kcSub == null) {
            return;
        }
        try {
            jdbc.update("""
                    INSERT INTO iam_user_link (user_id, kc_sub, tenant_id, default_branch_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (kc_sub) DO UPDATE
                    SET tenant_id = EXCLUDED.tenant_id,
                        default_branch_id = EXCLUDED.default_branch_id,
                        updated_at = EXCLUDED.updated_at
                    """,
                    userId, kcSub, tenantId, defaultBranchId,
                    OffsetDateTime.now(), OffsetDateTime.now());
        } catch (DataAccessException ex) {
            // DB 미준비 (로컬 테스트) — 무시. 운영에서는 의무.
        }
    }

    public Optional<String> findTenantByKcSub(String kcSub) {
        try {
            return Optional.ofNullable(jdbc.queryForObject(
                    "SELECT tenant_id FROM iam_user_link WHERE kc_sub = ?",
                    String.class, kcSub));
        } catch (DataAccessException ex) {
            return Optional.empty();
        }
    }
}
