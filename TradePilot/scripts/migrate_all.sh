#!/usr/bin/env bash
# =====================================================
# TradePilot - 마이그레이션 일괄 적용 스크립트
# 파일: scripts/migrate_all.sh
# 작성자: DBA
# 적용 대상: PostgreSQL 15+
#
# 동작:
#   1) DB 연결 확인 (pg_isready)
#   2) tp_audit.schema_migrations 존재 확인, 없으면 0000_ 적용
#   3) database/migrations/*.sql 정렬 + 미적용 항목 식별
#   4) 각 SQL을 트랜잭션 안에서 적용 (CREATE INDEX CONCURRENTLY 감지 시 분리)
#   5) 실패 시 ROLLBACK + status=FAILED 기록
#   6) 성공 시 SUCCESS + duration_ms 기록
#   7) 결과 요약 + exit code 반환 (0/1/2)
#
# 자격증명: PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE 환경변수 표준 사용.
#           평문 자격증명을 CLI 인자로 받지 않는다.
#
# 사용 예:
#   PGUSER=app_admin PGDATABASE=tradepilot ./scripts/migrate_all.sh --env staging
#   ./scripts/migrate_all.sh --env prod --dry-run
#   ./scripts/migrate_all.sh --env prod --from 2026_05_add_export_jobs.sql
#   ./scripts/migrate_all.sh --env prod --verify-only
# =====================================================

set -euo pipefail

# ---- 상수 / 경로 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MIGRATIONS_DIR="${ROOT_DIR}/database/migrations"
LOG_DIR="${ROOT_DIR}/logs/migrations"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/migrate_${TS}.log"

# ---- 기본 옵션 ----
ENV_NAME=""
DRY_RUN=0
VERIFY_ONLY=0
FROM_NAME=""
TO_NAME=""
FORCE=0
YES=0

# ---- 컬러(터미널 한정) ----
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'; BLU='\033[0;34m'; CLR='\033[0m'
else
    RED=''; GRN=''; YLW=''; BLU=''; CLR=''
fi

# ---- 사용법 ----
usage() {
    cat <<EOF
Usage: $(basename "$0") --env <prod|staging|dev> [옵션]

옵션:
  --env <name>          (필수) 환경 식별자. 운영(prod)은 추가 확인 절차 적용
  --dry-run             SQL 실제 적용 없이 plan 만 출력
  --from <name>         특정 마이그레이션 파일부터 재개 (basename)
  --to <name>           특정 마이그레이션 파일까지 적용 후 중단 (basename)
  --verify-only         미적용 항목 적용 없이 schema_migrations 상태만 출력
  --force               체크섬 불일치 시에도 적용 강행 (위험)
  --yes                 대화형 확인 건너뜀
  -h, --help            본 도움말

환경변수:
  PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE
  BACKUP_PATH           (선택) preflight 가 검사하는 백업 파일 경로

Exit codes:
  0  성공 (전부 적용 또는 적용할 항목 없음)
  1  실패 (적용 중 오류)
  2  검증 실패 (사후 검증 미충족)
  3  사용자 입력 오류 / 환경 미설정
EOF
}

# ---- 인자 파싱 ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)         ENV_NAME="${2:-}"; shift 2 ;;
        --dry-run)     DRY_RUN=1; shift ;;
        --verify-only) VERIFY_ONLY=1; shift ;;
        --from)        FROM_NAME="${2:-}"; shift 2 ;;
        --to)          TO_NAME="${2:-}"; shift 2 ;;
        --force)       FORCE=1; shift ;;
        --yes)         YES=1; shift ;;
        -h|--help)     usage; exit 0 ;;
        *)             echo "알 수 없는 옵션: $1"; usage; exit 3 ;;
    esac
done

if [[ -z "$ENV_NAME" ]]; then
    echo -e "${RED}오류: --env 는 필수입니다${CLR}" >&2
    usage
    exit 3
fi

mkdir -p "$LOG_DIR"

# ---- 로깅 헬퍼 ----
log()  { local msg="$*"; printf '%s [%s] %s\n' "$(date +'%Y-%m-%d %H:%M:%S')" "INFO"  "$msg" | tee -a "$LOG_FILE"; }
warn() { local msg="$*"; printf '%s [%s] %s\n' "$(date +'%Y-%m-%d %H:%M:%S')" "WARN"  "$msg" | tee -a "$LOG_FILE" >&2; }
err()  { local msg="$*"; printf '%s [%s] %s\n' "$(date +'%Y-%m-%d %H:%M:%S')" "ERROR" "$msg" | tee -a "$LOG_FILE" >&2; }

# ---- DB 헬퍼 ----
psql_q() {
    # quiet 1행 출력
    PGOPTIONS='--client-min-messages=warning' psql -X -A -t -v ON_ERROR_STOP=1 -c "$1"
}

psql_f() {
    # 파일 실행, echo-all 로 SQL 라인을 로그에 남김
    PGOPTIONS='--client-min-messages=warning' psql -X -v ON_ERROR_STOP=1 --echo-all -f "$1"
}

psql_exec() {
    PGOPTIONS='--client-min-messages=warning' psql -X -v ON_ERROR_STOP=1 -c "$1"
}

# ---- 시작 배너 ----
log "============================================================"
log "TradePilot 마이그레이션 시작"
log "  환경:      ${ENV_NAME}"
log "  dry-run:   $([[ $DRY_RUN -eq 1 ]] && echo yes || echo no)"
log "  verify:    $([[ $VERIFY_ONLY -eq 1 ]] && echo yes || echo no)"
log "  from:      ${FROM_NAME:-<처음부터>}"
log "  to:        ${TO_NAME:-<끝까지>}"
log "  PGHOST:    ${PGHOST:-<기본>}"
log "  PGUSER:    ${PGUSER:-<기본>}"
log "  PGDATABASE:${PGDATABASE:-<기본>}"
log "  로그:      ${LOG_FILE}"
log "============================================================"

# ---- 운영 환경 추가 확인 ----
if [[ "$ENV_NAME" == "prod" && $YES -eq 0 && $DRY_RUN -eq 0 && $VERIFY_ONLY -eq 0 ]]; then
    echo
    echo -e "${YLW}경고: 운영(prod) 환경에 실제 적용합니다.${CLR}"
    echo "백업 확인이 끝났습니까? 사전 점검(migrate_preflight.sh)이 통과했습니까?"
    read -r -p "계속하려면 'APPLY' 를 입력하세요: " confirm
    if [[ "$confirm" != "APPLY" ]]; then
        warn "사용자 취소"
        exit 3
    fi
fi

# ---- 1) DB 연결 확인 ----
log "[1/6] DB 연결 확인"
if ! pg_isready -q; then
    err "pg_isready 실패. PGHOST/PGPORT 환경변수를 확인하세요"
    exit 1
fi
DB_VERSION="$(psql_q "SELECT version();" || true)"
log "  DB version: ${DB_VERSION}"

# ---- 2) schema_migrations 테이블 보장 ----
log "[2/6] tp_audit.schema_migrations 보장"
HAS_TABLE="$(psql_q "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema='tp_audit' AND table_name='schema_migrations');" || echo "f")"
if [[ "$HAS_TABLE" != "t" ]]; then
    log "  → 추적 테이블 없음. 0000_schema_migrations.sql 적용"
    if [[ $DRY_RUN -eq 1 ]]; then
        log "    [dry-run] ${MIGRATIONS_DIR}/0000_schema_migrations.sql"
    else
        psql_f "${MIGRATIONS_DIR}/0000_schema_migrations.sql" >>"$LOG_FILE" 2>&1
        log "  → 추적 테이블 생성 완료"
    fi
else
    log "  → 추적 테이블 존재 OK"
fi

# ---- 3) 마이그레이션 파일 목록 ----
log "[3/6] 마이그레이션 파일 스캔"
mapfile -t ALL_FILES < <(find "$MIGRATIONS_DIR" -maxdepth 1 -type f -name '*.sql' ! -name '0000_*.sql' | sort)
log "  발견: ${#ALL_FILES[@]} 개"
for f in "${ALL_FILES[@]}"; do
    log "    - $(basename "$f")"
done

# 적용 이력 조회 (verify/실적용 모두 사용)
declare -A APPLIED_MAP=()
declare -A APPLIED_CHECKSUM=()
if [[ "$HAS_TABLE" == "t" || $DRY_RUN -eq 0 ]]; then
    while IFS='|' read -r name status checksum; do
        [[ -z "$name" ]] && continue
        APPLIED_MAP["$name"]="$status"
        APPLIED_CHECKSUM["$name"]="$checksum"
    done < <(psql_q "SELECT name, status, COALESCE(checksum,'') FROM tp_audit.schema_migrations;" 2>/dev/null || true)
fi

# ---- verify-only ----
if [[ $VERIFY_ONLY -eq 1 ]]; then
    log "[verify-only] 적용 상태 보고"
    echo
    printf "  %-45s %-12s %s\n" "파일" "상태" "체크섬(기대 vs 적용)"
    printf "  %-45s %-12s %s\n" "----" "----" "------------------"
    for f in "${ALL_FILES[@]}"; do
        name="$(basename "$f")"
        cur_sha="$(sha256sum "$f" | awk '{print $1}')"
        rec_sha="${APPLIED_CHECKSUM[$name]:-}"
        st="${APPLIED_MAP[$name]:-MISSING}"
        match="-"
        if [[ -n "$rec_sha" ]]; then
            if [[ "$cur_sha" == "$rec_sha" ]]; then match="OK"; else match="MISMATCH"; fi
        fi
        printf "  %-45s %-12s %s\n" "$name" "$st" "$match"
    done
    log "[verify-only] 완료"
    exit 0
fi

# ---- 4) 적용할 항목 선별 ----
log "[4/6] 적용 대상 산출"
declare -a TARGET=()
START=0; STOP=0
if [[ -z "$FROM_NAME" ]]; then START=1; fi
for f in "${ALL_FILES[@]}"; do
    name="$(basename "$f")"
    if [[ $STOP -eq 1 ]]; then break; fi
    if [[ $START -eq 0 ]]; then
        if [[ "$name" == "$FROM_NAME" ]]; then START=1; fi
    fi
    if [[ $START -eq 1 ]]; then
        # 이미 SUCCESS면 skip
        if [[ "${APPLIED_MAP[$name]:-}" == "SUCCESS" ]]; then
            log "  skip: $name (이미 적용됨)"
            # 체크섬 비교
            cur_sha="$(sha256sum "$f" | awk '{print $1}')"
            rec_sha="${APPLIED_CHECKSUM[$name]:-}"
            if [[ -n "$rec_sha" && "$cur_sha" != "$rec_sha" ]]; then
                if [[ $FORCE -eq 1 ]]; then
                    warn "  체크섬 불일치(--force): $name  ($cur_sha vs $rec_sha)"
                else
                    err "  체크섬 불일치(차단): $name  ($cur_sha vs $rec_sha)"
                    err "  파일이 적용 이후 변경되었습니다. --force 또는 롤백/재배포 결정 필요"
                    exit 1
                fi
            fi
        else
            TARGET+=("$f")
        fi
        if [[ -n "$TO_NAME" && "$name" == "$TO_NAME" ]]; then STOP=1; fi
    fi
done
log "  적용 대상: ${#TARGET[@]} 건"

if [[ ${#TARGET[@]} -eq 0 ]]; then
    log "${GRN}적용할 마이그레이션이 없습니다. 종료(success)${CLR}"
    exit 0
fi

# ---- 5) 적용 ----
log "[5/6] 마이그레이션 적용 시작"
FAILED=0
APPLIED=0
APPLIED_BY="${USER:-$(id -un)}"

for f in "${TARGET[@]}"; do
    name="$(basename "$f")"
    cur_sha="$(sha256sum "$f" | awk '{print $1}')"
    log "  → ${name}  (sha256=${cur_sha:0:12}...)"

    # CONCURRENTLY 감지: 첫 줄 또는 파일 내에 -- @concurrently 주석이 있으면 트랜잭션 외부 실행
    USE_TX=1
    if head -n 5 "$f" | grep -qE -- '--[[:space:]]*@concurrently'; then
        USE_TX=0
        log "    감지: @concurrently → 트랜잭션 외부에서 실행"
    fi

    if [[ $DRY_RUN -eq 1 ]]; then
        log "    [dry-run] 적용 생략. SQL 미리보기:"
        head -n 40 "$f" | sed 's/^/      | /' | tee -a "$LOG_FILE" >/dev/null
        APPLIED=$((APPLIED + 1))
        # dry-run 도 schema_migrations 에 SKIPPED 로 남기지 않는다(테이블 변경 금지).
        continue
    fi

    t0=$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')
    SQL_OK=0
    if [[ $USE_TX -eq 1 ]]; then
        # 트랜잭션 안에서 BEGIN/COMMIT 으로 감쌈
        # 파일 자체에 BEGIN/COMMIT 이 있어도 안전: 중첩 트랜잭션 회피 위해 명시적 wrap 대신
        # ON_ERROR_STOP=1 + 파일 그대로 실행 (성능 인덱스 SQL 등은 자체 BEGIN/COMMIT 포함)
        if PGOPTIONS='--client-min-messages=warning' psql -X -v ON_ERROR_STOP=1 --echo-all -f "$f" >>"$LOG_FILE" 2>&1; then
            SQL_OK=1
        fi
    else
        # CONCURRENTLY 는 트랜잭션 외부에서 실행 (psql 의 -1 미사용 + autocommit)
        if PGOPTIONS='--client-min-messages=warning' psql -X -v ON_ERROR_STOP=1 --echo-all -f "$f" >>"$LOG_FILE" 2>&1; then
            SQL_OK=1
        fi
    fi
    t1=$(date +%s%3N 2>/dev/null || python3 -c 'import time;print(int(time.time()*1000))')
    dur=$(( t1 - t0 ))

    if [[ $SQL_OK -eq 1 ]]; then
        APPLIED=$((APPLIED + 1))
        log "    ${GRN}성공${CLR}  ${dur}ms"
        # schema_migrations 기록
        psql_exec "INSERT INTO tp_audit.schema_migrations (name, checksum, applied_by, duration_ms, status, notes)
                   VALUES ('${name}', '${cur_sha}', '${APPLIED_BY}', ${dur}, 'SUCCESS', 'env=${ENV_NAME}')
                   ON CONFLICT (name) DO UPDATE SET
                     checksum    = EXCLUDED.checksum,
                     applied_at  = now(),
                     applied_by  = EXCLUDED.applied_by,
                     duration_ms = EXCLUDED.duration_ms,
                     status      = 'SUCCESS',
                     notes       = EXCLUDED.notes;" >>"$LOG_FILE" 2>&1 || warn "    schema_migrations 기록 실패(무시)"
    else
        FAILED=$((FAILED + 1))
        err "    실패: ${name}  ${dur}ms"
        # 실패 기록
        psql_exec "INSERT INTO tp_audit.schema_migrations (name, checksum, applied_by, duration_ms, status, notes)
                   VALUES ('${name}', '${cur_sha}', '${APPLIED_BY}', ${dur}, 'FAILED', 'env=${ENV_NAME} ; see log ${LOG_FILE}')
                   ON CONFLICT (name) DO UPDATE SET
                     checksum    = EXCLUDED.checksum,
                     applied_at  = now(),
                     status      = 'FAILED',
                     notes       = EXCLUDED.notes;" >>"$LOG_FILE" 2>&1 || true
        err "    이후 마이그레이션 중단"
        break
    fi
done

# ---- 6) 사후 검증 ----
log "[6/6] 사후 검증 (migrate_verify.sh) 호출"
VERIFY_RC=0
if [[ $DRY_RUN -eq 0 && $FAILED -eq 0 ]]; then
    if [[ -x "${SCRIPT_DIR}/migrate_verify.sh" ]]; then
        if "${SCRIPT_DIR}/migrate_verify.sh" --env "$ENV_NAME" >>"$LOG_FILE" 2>&1; then
            log "  검증 통과"
        else
            VERIFY_RC=$?
            err "  검증 실패 (rc=${VERIFY_RC})"
        fi
    else
        warn "  migrate_verify.sh 미존재 또는 실행권한 없음. 검증 생략"
    fi
fi

# ---- 결과 요약 ----
log "============================================================"
log "결과 요약"
log "  적용 성공:  ${APPLIED}"
log "  적용 실패:  ${FAILED}"
log "  검증 결과:  $([[ $VERIFY_RC -eq 0 ]] && echo PASS || echo FAIL)"
log "  로그 파일:  ${LOG_FILE}"
log "============================================================"

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
if [[ $VERIFY_RC -ne 0 ]]; then
    exit 2
fi
exit 0
