#!/usr/bin/env bash
# npm_audit.sh — 프론트엔드 의존성 취약점 스캔
#
# 사용법:
#   bash TradePilot/security/scripts/npm_audit.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
FE="$ROOT/TradePilot/frontend"

if ! command -v npm >/dev/null 2>&1; then
    echo "[npm] 미설치 — Node 20 + npm 필요"
    exit 2
fi

REPORT_DIR="$ROOT/TradePilot/security/reports"
mkdir -p "$REPORT_DIR"

pushd "$FE" >/dev/null

echo "[npm audit] running ..."
EXIT=0
# moderate 이상 취약점만 실패 처리. Low 는 정보 표시.
npm audit --audit-level=moderate --json > "$REPORT_DIR/npm-audit.json" || EXIT=$?
npm audit --audit-level=moderate | tee "$REPORT_DIR/npm-audit.txt" || true

popd >/dev/null

echo
echo "[npm audit] 리포트: $REPORT_DIR/npm-audit.{json,txt}"
exit $EXIT
