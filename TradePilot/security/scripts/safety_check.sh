#!/usr/bin/env bash
# safety_check.sh — Python 의존성 취약점 스캔 (pip-audit)
#
# 사용법:
#   bash TradePilot/security/scripts/safety_check.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

if ! command -v pip-audit >/dev/null 2>&1; then
    echo "[pip-audit] 미설치 — 'pip install pip-audit==2.7.*' 필요"
    exit 2
fi

REPORT_DIR="$ROOT/TradePilot/security/reports"
mkdir -p "$REPORT_DIR"

EXIT=0

for project in backend creon-gateway; do
    echo "[pip-audit] scanning $project ..."
    pushd "$ROOT/TradePilot/$project" >/dev/null
    pip-audit --strict \
        --format json \
        --output "$REPORT_DIR/pip-audit-${project}.json" \
        || EXIT=$?
    pip-audit --strict --format columns \
        | tee "$REPORT_DIR/pip-audit-${project}.txt" \
        || true
    popd >/dev/null
done

echo
echo "[pip-audit] 리포트: $REPORT_DIR/pip-audit-*.{json,txt}"
exit $EXIT
