#!/usr/bin/env bash
# gitleaks_scan.sh — 시크릿 누출 스캔 (git 히스토리 + working tree)
#
# 사용법:
#   bash TradePilot/security/scripts/gitleaks_scan.sh [--no-git]
#
# 옵션:
#   --no-git : 워킹 트리만 스캔 (히스토리 스캔 생략, 빠름)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"

if ! command -v gitleaks >/dev/null 2>&1; then
    echo "[gitleaks] 미설치 — 'brew install gitleaks' 또는 https://github.com/gitleaks/gitleaks/releases"
    exit 2
fi

REPORT_DIR="$ROOT/TradePilot/security/reports"
mkdir -p "$REPORT_DIR"

EXTRA=""
if [[ "${1:-}" == "--no-git" ]]; then
    EXTRA="--no-git"
fi

echo "[gitleaks] scanning ..."
gitleaks detect \
    --source "$ROOT" \
    $EXTRA \
    --report-format json \
    --report-path "$REPORT_DIR/gitleaks.json" \
    --redact \
    --verbose \
    || EXIT=$?

EXIT=${EXIT:-0}

if [[ $EXIT -ne 0 ]]; then
    echo
    echo "[gitleaks] 시크릿 발견. 리포트: $REPORT_DIR/gitleaks.json"
fi

exit $EXIT
