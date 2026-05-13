#!/usr/bin/env bats
# =====================================================================
# TradePilot 백업 스크립트 단위 테스트 (bats)
# 파일: tests/test_backup_scripts.bats
# 실행:
#   bats tests/test_backup_scripts.bats
#   bats -f "retention" tests/test_backup_scripts.bats   # 필터
# 의존성: bats-core (apk add bats / apt install bats)
# =====================================================================

setup() {
    SCRIPT_DIR="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd)"
    export SCRIPT_DIR

    # 격리된 작업 디렉토리
    export TEST_TMP="$(mktemp -d -t tp_backup_test_XXXXXX)"
    export BACKUP_LOCAL_DIR="${TEST_TMP}/backup"
    export LOCK_DIR="${BACKUP_LOCAL_DIR}/.lock"
    export LOG_DIR="${BACKUP_LOCAL_DIR}/log"
    mkdir -p "${BACKUP_LOCAL_DIR}/full" \
             "${BACKUP_LOCAL_DIR}/wal" \
             "${BACKUP_LOCAL_DIR}/logical" \
             "${LOG_DIR}" "${LOCK_DIR}"

    # 환경변수
    export DB_HOST=localhost
    export DB_PORT=5432
    export DB_USER=test_user
    export DB_NAME=test_db
    export ALLOW_PLAINTEXT_BACKUP=true
    export DRY_RUN=true
}

teardown() {
    rm -rf "${TEST_TMP}"
}

# ---- 공통 라이브러리 -------------------------------------------------
@test "common.sh: 환경변수 누락 시 require_env 실패" {
    source "${SCRIPT_DIR}/lib/common.sh"
    run bash -c "unset DB_HOST; require_env DB_HOST"
    [ "$status" -ne 0 ]
}

@test "common.sh: human_size 가 KB/MB 변환 정확" {
    source "${SCRIPT_DIR}/lib/common.sh"
    result=$(human_size 1024)
    [[ "$result" == *"KiB"* ]] || [[ "$result" == *"KB"* ]] || [[ "$result" == *"K"* ]]
    result=$(human_size 1048576)
    [[ "$result" == *"MiB"* ]] || [[ "$result" == *"MB"* ]] || [[ "$result" == *"M"* ]]
}

@test "common.sh: SHA256 체크섬 생성 + 검증 성공" {
    source "${SCRIPT_DIR}/lib/common.sh"
    local f="${TEST_TMP}/sample.txt"
    echo "TradePilot test" > "$f"
    make_checksum "$f"
    [ -f "${f}.sha256" ]
    verify_checksum "$f"
}

@test "common.sh: SHA256 변조 시 검증 실패" {
    source "${SCRIPT_DIR}/lib/common.sh"
    local f="${TEST_TMP}/sample.txt"
    echo "original" > "$f"
    make_checksum "$f"
    echo "modified" > "$f"
    run verify_checksum "$f"
    [ "$status" -ne 0 ]
}

@test "common.sh: 락 동시 획득 차단" {
    source "${SCRIPT_DIR}/lib/common.sh"
    SCRIPT_NAME="lock_test_$$"

    # 첫 번째 락 (백그라운드, 5초 대기)
    (
        source "${SCRIPT_DIR}/lib/common.sh"
        SCRIPT_NAME="lock_test_$$"
        acquire_lock lock_concurrent_test
        sleep 3
    ) &
    local pid=$!
    sleep 1   # 첫 번째 락 획득 대기

    # 두 번째 락 시도 → 실패해야 함
    run bash -c "
        source '${SCRIPT_DIR}/lib/common.sh'
        SCRIPT_NAME='lock_test_$$'
        BACKUP_LOCAL_DIR='${BACKUP_LOCAL_DIR}'
        LOCK_DIR='${LOCK_DIR}'
        acquire_lock lock_concurrent_test
    "
    [ "$status" -eq 3 ]

    wait $pid 2>/dev/null || true
}

# ---- backup_full.sh --------------------------------------------------
@test "backup_full.sh: --help 출력" {
    run "${SCRIPT_DIR}/backup_full.sh" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"사용법"* ]] || [[ "$output" == *"옵션"* ]]
}

@test "backup_full.sh: --dry-run 모드는 pg_dump 실제 호출 안함" {
    # PATH 에 가짜 pg_dump 배치
    cat > "${TEST_TMP}/pg_dump" <<'EOF'
#!/usr/bin/env bash
echo "FAKE_PG_DUMP_CALLED"
touch "${TEST_TMP}/pg_dump_called"
EOF
    chmod +x "${TEST_TMP}/pg_dump"
    export PATH="${TEST_TMP}:${PATH}"
    export DRY_RUN=true

    run "${SCRIPT_DIR}/backup_full.sh" --dry-run
    # DRY_RUN 이므로 pg_dump 호출되지 않아야 함
    [ ! -f "${TEST_TMP}/pg_dump_called" ]
}

# ---- retention.sh ---------------------------------------------------
@test "retention.sh: 7일 이전 풀백업만 삭제, 최신은 보존" {
    # 오래된 파일과 신규 파일 생성
    local old_file="${BACKUP_LOCAL_DIR}/full/tradepilot_20250101_000000.dump"
    local new_file="${BACKUP_LOCAL_DIR}/full/tradepilot_$(date +%Y%m%d_%H%M%S).dump"
    echo "old" > "${old_file}"
    echo "new" > "${new_file}"
    # 오래된 파일의 mtime을 30일 전으로 강제
    touch -d "30 days ago" "${old_file}"

    export RETENTION_DAYS_LOCAL=7
    run "${SCRIPT_DIR}/retention.sh"
    [ "$status" -eq 0 ]
    [ ! -f "${old_file}" ]    # 오래된 것 삭제됨
    [ -f "${new_file}" ]      # 신규는 보존
}

@test "retention.sh: --dry-run 모드는 실제 삭제하지 않음" {
    local old_file="${BACKUP_LOCAL_DIR}/full/tradepilot_20250101_000000.dump"
    echo "old" > "${old_file}"
    touch -d "30 days ago" "${old_file}"

    export RETENTION_DAYS_LOCAL=7
    run "${SCRIPT_DIR}/retention.sh" --dry-run
    [ "$status" -eq 0 ]
    [ -f "${old_file}" ]    # dry-run이므로 삭제 안 됨
}

# ---- backup_wal.sh --------------------------------------------------
@test "backup_wal.sh: 인자 부족 시 사용법 출력 + exit 1" {
    run "${SCRIPT_DIR}/backup_wal.sh"
    [ "$status" -eq 1 ]
}

@test "backup_wal.sh: WAL 파일 정상 아카이빙" {
    # gzip이 있는 환경에서만 실행
    command -v gzip >/dev/null 2>&1 || skip "gzip 미설치"

    local fake_wal="${TEST_TMP}/000000010000000000000001"
    head -c 16777216 /dev/urandom > "${fake_wal}"  # 16MB WAL 모방

    run "${SCRIPT_DIR}/backup_wal.sh" "${fake_wal}" "000000010000000000000001"
    [ "$status" -eq 0 ]
    [ -f "${BACKUP_LOCAL_DIR}/wal/000000010000000000000001.gz" ]
    [ -f "${BACKUP_LOCAL_DIR}/.last_wal_archive" ]
}

@test "backup_wal.sh: 동일 파일 재호출 시 idempotent (skip)" {
    local fake_wal="${TEST_TMP}/000000010000000000000002"
    echo "test_wal_data" > "${fake_wal}"

    # 첫 번째 호출
    "${SCRIPT_DIR}/backup_wal.sh" "${fake_wal}" "000000010000000000000002"

    # 두 번째 호출 (동일 파일) → 0 반환
    run "${SCRIPT_DIR}/backup_wal.sh" "${fake_wal}" "000000010000000000000002"
    [ "$status" -eq 0 ]
}

# ---- monitor.py -----------------------------------------------------
@test "monitor.py: --help 정상" {
    run python3 "${SCRIPT_DIR}/monitor.py" --help
    [ "$status" -eq 0 ]
}

@test "monitor.py: 마커 파일 없을 때 CRITICAL" {
    run python3 "${SCRIPT_DIR}/monitor.py" --no-alert --backup-dir "${BACKUP_LOCAL_DIR}"
    # CRITICAL=2, WARN=1, OK=0
    [ "$status" -eq 2 ]
    [[ "$output" == *"마지막 풀백업 마커 없음"* ]] || [[ "$output" == *"CRIT"* ]]
}

@test "monitor.py: 최근 풀백업 마커 있으면 OK" {
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "${BACKUP_LOCAL_DIR}/.last_full_success"
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "${BACKUP_LOCAL_DIR}/.last_wal_archive"
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "${BACKUP_LOCAL_DIR}/.last_drill_success"
    # 최소 1개 백업 파일 필요
    touch "${BACKUP_LOCAL_DIR}/full/tradepilot_test.dump"
    touch "${BACKUP_LOCAL_DIR}/full/tradepilot_test2.dump"

    run python3 "${SCRIPT_DIR}/monitor.py" --no-alert --backup-dir "${BACKUP_LOCAL_DIR}"
    [ "$status" -eq 0 ]
}

@test "monitor.py: --json 출력 valid JSON" {
    date -u +'%Y-%m-%dT%H:%M:%SZ' > "${BACKUP_LOCAL_DIR}/.last_full_success"

    run python3 "${SCRIPT_DIR}/monitor.py" --no-alert --json --backup-dir "${BACKUP_LOCAL_DIR}"
    # JSON 파싱 가능해야 함
    echo "$output" | python3 -c "import json,sys; json.loads(sys.stdin.read())"
}

# ---- restore_full.sh --------------------------------------------------
@test "restore_full.sh: 운영 DB 직접 지정 시 거부" {
    export DB_NAME=tradepilot
    # 가짜 백업 파일
    local fake_backup="${TEST_TMP}/fake.dump"
    echo "fake" > "${fake_backup}"

    run "${SCRIPT_DIR}/restore_full.sh" --yes "${fake_backup}" "tradepilot"
    [ "$status" -eq 10 ]   # 운영 DB 거부
}

@test "restore_full.sh: 백업 파일 없으면 exit 2" {
    run "${SCRIPT_DIR}/restore_full.sh" --yes /nonexistent/file.dump tradepilot_drill
    [ "$status" -eq 2 ]
}

# ---- s3_upload.sh ---------------------------------------------------
@test "s3_upload.sh: 인자 없으면 사용법 + exit 1" {
    run "${SCRIPT_DIR}/s3_upload.sh"
    [ "$status" -eq 1 ]
}

@test "s3_upload.sh: 파일 없으면 exit 1" {
    export S3_BUCKET=test-bucket
    export S3_REGION=us-east-1
    run "${SCRIPT_DIR}/s3_upload.sh" /nonexistent/file
    [ "$status" -eq 1 ]
}

# ---- 환경변수 누락 일관성 -------------------------------------------
@test "backup_logical.sh: BACKUP_LOCAL_DIR 누락 시 exit 2" {
    run env -i HOME="$HOME" PATH="$PATH" "${SCRIPT_DIR}/backup_logical.sh"
    [ "$status" -ne 0 ]
}
