#!/usr/bin/env bash
# =====================================================================
# TradePilot 단일 테이블 복구 (pg_restore -t)
# 파일: restore_table.sh
# 목적:
#   특정 테이블만 임시 DB에 복원 → 검증 → 운영 DB로 INSERT/MERGE.
#   주의: pg_restore -t는 의존(FK/시퀀스/인덱스) 자동 처리하지 않음.
#
# 사용법:
#   ./restore_table.sh <backup_file> <schema.table> [--target-db tp_temp]
#   ./restore_table.sh /var/backup/.../tradepilot.dump.gpg tp_trade.orders
#   ./restore_table.sh --data-only ... tp_trade.orders
#
# 옵션:
#   --target-db <name>  복원 대상 DB(기본: tradepilot_table_restore_<stamp>)
#   --data-only         데이터만 (스키마 없이)
#   --schema-only       스키마만 (데이터 없이)
#   --jobs N            병렬도(기본 2)
#
# 권장 워크플로우:
#   1) 본 스크립트로 임시 DB 에 테이블 복원
#   2) 운영 DB 와 diff 확인
#   3) 필요한 행만 SELECT INTO / INSERT ... ON CONFLICT
#   4) 임시 DB DROP
# =====================================================================

SCRIPT_NAME="restore_table.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DATA_ONLY=false
SCHEMA_ONLY=false
JOBS=2
TARGET_DB=""
POSITIONAL=()

usage() {
    cat <<EOF
사용법: $0 [옵션] <backup_file> <schema.table> [<schema.table> ...]

옵션:
  --target-db <name>  복원 대상 DB (기본: tp_table_restore_<timestamp>)
  --data-only         데이터만 복원
  --schema-only       스키마만 복원
  --jobs N            병렬 복원 jobs
  --yes               확인 프롬프트 생략
  -h|--help           도움말
EOF
}

ASSUME_YES=false
while (( $# > 0 )); do
    case "$1" in
        --target-db) shift; TARGET_DB="$1" ;;
        --data-only) DATA_ONLY=true ;;
        --schema-only) SCHEMA_ONLY=true ;;
        --jobs) shift; JOBS="$1" ;;
        --yes) ASSUME_YES=true ;;
        --dry-run) DRY_RUN=true ;;
        -h|--help) usage; exit 0 ;;
        -*) log_error "알 수 없는 옵션: $1"; exit 1 ;;
        *) POSITIONAL+=("$1") ;;
    esac
    shift
done

(( ${#POSITIONAL[@]} >= 2 )) || { usage; exit 1; }
BACKUP_FILE="${POSITIONAL[0]}"
TABLES=("${POSITIONAL[@]:1}")

main() {
    log_setup
    load_env
    require_env DB_HOST DB_PORT DB_USER
    export_pgpassword

    [[ -f "${BACKUP_FILE}" ]] || { log_error "백업 파일 없음: ${BACKUP_FILE}"; exit 2; }

    [[ -z "${TARGET_DB}" ]] && TARGET_DB="tp_table_restore_$(date +%Y%m%d_%H%M%S)"

    log_info "복원 대상: DB=${TARGET_DB}, 테이블=${TABLES[*]}"

    # ---- 복호화 ---------------------------------------------------
    local work_dir
    work_dir="$(mktemp -d -t tp_restore_table_XXXXXX)"
    trap "rm -rf '${work_dir}'" EXIT

    local dump_file="${BACKUP_FILE}"
    case "${BACKUP_FILE}" in
        *.gpg|*.age)
            local plain
            plain="${work_dir}/$(basename "${BACKUP_FILE%.gpg}")"
            plain="${plain%.age}"
            decrypt_file "${BACKUP_FILE}" "${plain}" >/dev/null
            dump_file="${plain}"
            ;;
    esac

    # ---- 대상 DB 생성 (이미 있으면 거부) -------------------------
    local exists
    exists=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -At \
        -c "SELECT 1 FROM pg_database WHERE datname='${TARGET_DB}'")
    if [[ "${exists}" == "1" ]]; then
        log_error "대상 DB(${TARGET_DB}) 가 이미 존재합니다."
        exit 12
    fi

    if [[ "${ASSUME_YES}" != "true" ]]; then
        read -r -p "임시 DB ${TARGET_DB} 를 만들고 ${#TABLES[@]}개 테이블을 복원합니다. 계속? [yes/no]: " ans
        [[ "${ans}" == "yes" ]] || exit 0
    fi

    run_cmd psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
        -c "CREATE DATABASE \"${TARGET_DB}\" TEMPLATE template0;"

    # ---- pg_restore -t 옵션 구성 ----------------------------------
    local pg_opts=(
        -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}"
        -d "${TARGET_DB}"
        --jobs="${JOBS}"
        --no-owner --no-privileges
        --verbose
    )
    [[ "${DATA_ONLY}"   == "true" ]] && pg_opts+=(--data-only)
    [[ "${SCHEMA_ONLY}" == "true" ]] && pg_opts+=(--schema-only)

    # 각 테이블 -t 추가 (schema.table 분리)
    local t schema name
    for t in "${TABLES[@]}"; do
        if [[ "$t" == *.* ]]; then
            schema="${t%%.*}"
            name="${t##*.}"
            pg_opts+=(-n "${schema}" -t "${name}")
        else
            pg_opts+=(-t "${t}")
        fi
    done

    log_info "pg_restore 시작 (jobs=${JOBS})"
    if ! run_cmd pg_restore "${pg_opts[@]}" "${dump_file}"; then
        log_error "pg_restore 실패"
        exit 5
    fi

    # ---- 복원 결과 카운트 -----------------------------------------
    log_info "복원된 테이블 행 수:"
    for t in "${TABLES[@]}"; do
        local count
        count=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TARGET_DB}" -At \
            -c "SELECT COUNT(*) FROM ${t}" 2>/dev/null || echo "ERROR")
        log_info "  ${t}: ${count}"
    done

    log_ok "단일 테이블 복원 완료: ${TARGET_DB}"
    cat <<EOF

[다음 단계]
  1) 운영 DB 와 diff 확인:
       psql -d ${DB_NAME:-tradepilot} -c "SELECT COUNT(*) FROM <table>"
       psql -d ${TARGET_DB} -c "SELECT COUNT(*) FROM <table>"
  2) 필요한 행만 INSERT (예시):
       INSERT INTO ${DB_NAME:-tradepilot}.<schema>.<table>
       SELECT * FROM dblink('dbname=${TARGET_DB}', 'SELECT * FROM ...')
       AS t(...) ON CONFLICT DO NOTHING;
  3) 검증 후 임시 DB 삭제:
       DROP DATABASE "${TARGET_DB}";
EOF
}

main
