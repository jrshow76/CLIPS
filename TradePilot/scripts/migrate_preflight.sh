#!/usr/bin/env bash
# =====================================================
# TradePilot - 마이그레이션 사전 점검 스크립트
# 파일: scripts/migrate_preflight.sh
# 작성자: DBA
#
# 점검 항목:
#   [P1] DB 연결 (pg_isready)
#   [P2] DB 권한 (CREATE / ALTER / INSERT 시도)
#   [P3] 디스크 여유 (호스트 df + pg_database_size)
#   [P4] 활성 트랜잭션 (idle in transaction 30분 이상 차단)
#   [P5] 백업 파일 (BACKUP_PATH 또는 /backup/postgres/latest.dump)
#   [P6] pg_stat_statements 활성 (선택, FAIL 시 WARN)
#   [P7] schema_migrations 테이블 존재(선택)
#
# 종료 코드:
#   0 모든 점검 PASS (또는 P6/P7 WARN만 발생)
#   1 점검 FAIL 존재
# =====================================================

set -euo pipefail

# ---- 옵션 ----
ENV_NAME=""
DISK_MIN_PCT=20      # 호스트 디스크 여유 최소 %
TX_IDLE_LIMIT_SEC=1800  # 30분 이상 idle-in-transaction 차단

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)             ENV_NAME="${2:-}"; shift 2 ;;
        --min-disk-pct)    DISK_MIN_PCT="${2:-20}"; shift 2 ;;
        --tx-idle-sec)     TX_IDLE_LIMIT_SEC="${2:-1800}"; shift 2 ;;
        -h|--help)
            cat <<EOF
Usage: $(basename "$0") --env <prod|staging|dev> [--min-disk-pct N] [--tx-idle-sec N]
환경변수: PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE, BACKUP_PATH
EOF
            exit 0 ;;
        *) echo "알 수 없는 옵션: $1"; exit 1 ;;
    esac
done

if [[ -z "$ENV_NAME" ]]; then
    echo "오류: --env 는 필수" >&2
    exit 1
fi

# ---- 컬러 ----
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'; CLR='\033[0m'
else
    RED=''; GRN=''; YLW=''; CLR=''
fi

PASS_CNT=0
FAIL_CNT=0
WARN_CNT=0

record_pass() { PASS_CNT=$((PASS_CNT+1)); printf "%b\n" "  [${GRN}PASS${CLR}] $1"; }
record_fail() { FAIL_CNT=$((FAIL_CNT+1)); printf "%b\n" "  [${RED}FAIL${CLR}] $1"; }
record_warn() { WARN_CNT=$((WARN_CNT+1)); printf "%b\n" "  [${YLW}WARN${CLR}] $1"; }

psql_q() {
    PGOPTIONS='--client-min-messages=warning' psql -X -A -t -v ON_ERROR_STOP=1 -c "$1" 2>/dev/null || echo ""
}

echo "============================================================"
echo "TradePilot 마이그레이션 사전 점검"
echo "  환경:       ${ENV_NAME}"
echo "  최소 디스크:${DISK_MIN_PCT}%"
echo "  idle TX 제한:${TX_IDLE_LIMIT_SEC}초"
echo "============================================================"

# ---- [P1] DB 연결 ----
echo "[P1] DB 연결 (pg_isready)"
if pg_isready -q; then
    record_pass "pg_isready OK (host=${PGHOST:-default}, db=${PGDATABASE:-default})"
else
    record_fail "pg_isready 실패. PGHOST/PGPORT/PGUSER 확인 필요"
fi

# 후속 점검은 연결 가능할 때만 진행
if [[ $FAIL_CNT -gt 0 ]]; then
    echo
    echo "DB 연결 실패. 후속 점검 건너뜀"
    echo "결과: FAIL=${FAIL_CNT} WARN=${WARN_CNT} PASS=${PASS_CNT}"
    exit 1
fi

# ---- [P2] DB 권한 ----
echo "[P2] DB 권한 (CREATE / INSERT / DROP 시도, tp_audit.preflight_probe)"
# 임시 테이블로 CREATE/INSERT/DROP 권한을 검증
PROBE_SQL=$(cat <<'SQL'
BEGIN;
CREATE SCHEMA IF NOT EXISTS tp_audit;
CREATE TABLE IF NOT EXISTS tp_audit.preflight_probe (id SERIAL PRIMARY KEY, t TIMESTAMPTZ NOT NULL DEFAULT now());
INSERT INTO tp_audit.preflight_probe DEFAULT VALUES;
DROP TABLE tp_audit.preflight_probe;
COMMIT;
SQL
)
if PGOPTIONS='--client-min-messages=warning' psql -X -v ON_ERROR_STOP=1 -c "$PROBE_SQL" >/dev/null 2>&1; then
    record_pass "CREATE/INSERT/DROP 권한 OK (user=${PGUSER:-default})"
else
    record_fail "스키마 변경 권한 부족. app_admin 또는 superuser 필요"
fi

# ---- [P3] 디스크 여유 ----
echo "[P3] 디스크 여유"
# 호스트 df (PGDATA 마운트가 알려진 환경이면 별도 옵션으로)
HOST_FREE_PCT="$(df -P / 2>/dev/null | awk 'NR==2 { gsub("%","",$5); print 100 - $5 }')"
if [[ -n "$HOST_FREE_PCT" ]]; then
    if [[ $HOST_FREE_PCT -ge $DISK_MIN_PCT ]]; then
        record_pass "호스트 / 마운트 여유 ${HOST_FREE_PCT}% (>= ${DISK_MIN_PCT}%)"
    else
        record_fail "호스트 / 마운트 여유 ${HOST_FREE_PCT}% (< ${DISK_MIN_PCT}%)"
    fi
else
    record_warn "df 결과를 파싱하지 못함"
fi

DB_SIZE="$(psql_q "SELECT pg_size_pretty(pg_database_size(current_database()));")"
if [[ -n "$DB_SIZE" ]]; then
    record_pass "현재 DB 크기: ${DB_SIZE}"
else
    record_warn "pg_database_size 조회 실패"
fi

# ---- [P4] 활성 트랜잭션 ----
echo "[P4] 활성 트랜잭션 / idle-in-transaction"
IDLE_TX_CNT="$(psql_q "SELECT count(*) FROM pg_stat_activity
                       WHERE state = 'idle in transaction'
                         AND now() - xact_start > interval '${TX_IDLE_LIMIT_SEC} seconds';")"
IDLE_TX_CNT="${IDLE_TX_CNT:-0}"
if [[ "$IDLE_TX_CNT" -eq 0 ]]; then
    record_pass "장시간(>${TX_IDLE_LIMIT_SEC}s) idle-in-transaction 없음"
else
    record_fail "장시간 idle-in-transaction ${IDLE_TX_CNT}건 (락 충돌 위험)"
fi

ACTIVE_CNT="$(psql_q "SELECT count(*) FROM pg_stat_activity WHERE state='active' AND pid <> pg_backend_pid();")"
ACTIVE_CNT="${ACTIVE_CNT:-0}"
if [[ "$ACTIVE_CNT" -le 20 ]]; then
    record_pass "활성 쿼리 ${ACTIVE_CNT}건"
else
    record_warn "활성 쿼리 ${ACTIVE_CNT}건 (마이그레이션 적용 시 충돌 가능)"
fi

# ---- [P5] 백업 파일 ----
echo "[P5] 백업 파일 존재"
BK_PATH="${BACKUP_PATH:-/backup/postgres/latest.dump}"
if [[ -f "$BK_PATH" ]]; then
    BK_SIZE="$(du -h "$BK_PATH" 2>/dev/null | awk '{print $1}')"
    BK_AGE=$(( $(date +%s) - $(stat -c %Y "$BK_PATH" 2>/dev/null || echo 0) ))
    BK_AGE_HOUR=$(( BK_AGE / 3600 ))
    if [[ $BK_AGE_HOUR -le 24 ]]; then
        record_pass "백업 OK: ${BK_PATH} (size=${BK_SIZE}, age=${BK_AGE_HOUR}h)"
    else
        record_fail "백업 노후: ${BK_PATH} (age=${BK_AGE_HOUR}h > 24h)"
    fi
else
    if [[ "$ENV_NAME" == "prod" ]]; then
        record_fail "백업 파일 없음: ${BK_PATH} (운영 적용 차단)"
    else
        record_warn "백업 파일 없음: ${BK_PATH} (비운영 환경, 경고)"
    fi
fi

# ---- [P6] pg_stat_statements ----
echo "[P6] pg_stat_statements (선택)"
PSS="$(psql_q "SELECT count(*) FROM pg_extension WHERE extname='pg_stat_statements';")"
PSS="${PSS:-0}"
if [[ "$PSS" -ge 1 ]]; then
    record_pass "pg_stat_statements 활성"
else
    record_warn "pg_stat_statements 미설치. 슬로우 쿼리 추적 제한"
fi

# ---- [P7] schema_migrations 존재 여부 ----
echo "[P7] tp_audit.schema_migrations (선택)"
HAS_TBL="$(psql_q "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='tp_audit' AND table_name='schema_migrations');")"
if [[ "$HAS_TBL" == "t" ]]; then
    record_pass "추적 테이블 존재"
else
    record_warn "추적 테이블 없음. migrate_all.sh 첫 실행 시 자동 생성됨"
fi

# ---- 요약 ----
echo "============================================================"
echo "사전 점검 결과: PASS=${PASS_CNT} WARN=${WARN_CNT} FAIL=${FAIL_CNT}"
echo "============================================================"

if [[ $FAIL_CNT -gt 0 ]]; then
    exit 1
fi
exit 0
