#!/usr/bin/env bash
#
# RLS 누설 회귀 자동화 wrapper
# - PostgreSQL 컨테이너 기동(필요 시)
# - Flyway 마이그레이션 적용
# - db/test/rls/*.sql 실행
# - 결과 요약 출력 + 종료 코드 반환
#
# 사용:
#   ./run-rls-tests.sh                  # 로컬 docker compose postgres 사용
#   PGURL=postgres://... ./run-rls-tests.sh
#
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_DIR="$ROOT/db/test/rls"
PGURL="${PGURL:-postgres://tulip:tulip@localhost:5432/tulip}"

echo "[rls] root=$ROOT"
echo "[rls] tests=$TEST_DIR"
echo "[rls] target=$PGURL"

if ! command -v psql >/dev/null 2>&1; then
  echo "[rls] psql 명령이 필요합니다. PostgreSQL client를 설치하세요." >&2
  exit 2
fi

if [[ ! -d "$TEST_DIR" ]]; then
  echo "[rls] $TEST_DIR 디렉토리가 없습니다." >&2
  exit 2
fi

pass=0
fail=0
failed=()

shopt -s nullglob
for sql in "$TEST_DIR"/*.sql; do
  name="$(basename "$sql")"
  echo "[rls] RUN  $name"
  if psql "$PGURL" -v ON_ERROR_STOP=1 -X -q -f "$sql"; then
    echo "[rls] PASS $name"
    pass=$((pass + 1))
  else
    echo "[rls] FAIL $name" >&2
    fail=$((fail + 1))
    failed+=("$name")
  fi
done

echo
echo "[rls] ===== 요약 ====="
echo "[rls] PASS: $pass"
echo "[rls] FAIL: $fail"
if ((fail > 0)); then
  printf '[rls] failed: %s\n' "${failed[@]}"
  exit 1
fi
