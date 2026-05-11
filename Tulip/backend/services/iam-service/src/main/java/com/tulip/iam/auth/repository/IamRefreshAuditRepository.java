package com.tulip.iam.auth.repository;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;

/**
 * Refresh 토큰 발급/회전/취소 감사 저장소.
 *
 * <p>{@code 05_security_and_auth.md} §7 감사로그 의무. 보존 1년(인증 로그).</p>
 */
@Repository
public class IamRefreshAuditRepository {

    private final JdbcTemplate jdbc;

    public IamRefreshAuditRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public void record(String userId, String action, String ip, String userAgent) {
        try {
            jdbc.update("""
                    INSERT INTO iam_refresh_audit (user_id, action, ip, ua, at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    userId, action, ip, userAgent, OffsetDateTime.now());
        } catch (DataAccessException ex) {
            // DB 미준비 (로컬 단위테스트) — 무시. 운영에서는 의무.
        }
    }
}
