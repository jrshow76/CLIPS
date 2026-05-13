#!/usr/bin/env bash
# bandit_scan.sh — Python 정적 보안 스캔
#
# 사용법:
#   bash TradePilot/security/scripts/bandit_scan.sh [target_dir]
#
# 기본: backend + creon-gateway 모두 스캔.
# Critical/High 만 실패 처리. Medium 이하는 경고.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TARGETS=(
    "$ROOT/TradePilot/backend/app"
    "$ROOT/TradePilot/creon-gateway/creon_gateway"
)

if ! command -v bandit >/dev/null 2>&1; then
    echo "[bandit] 미설치 — 'pip install bandit==1.7.*' 필요"
    exit 2
fi

REPORT_DIR="$ROOT/TradePilot/security/reports"
mkdir -p "$REPORT_DIR"

EXIT=0
for t in "${TARGETS[@]}"; do
    name=$(basename "$(dirname "$t")")
    echo "[bandit] scanning $name ..."
    bandit -r "$t" \
        -f json \
        -o "$REPORT_DIR/bandit-${name}.json" \
        --severity-level high \
        --confidence-level medium \
        --skip B101,B601 \
        || EXIT=$?
    # 사람용 요약
    bandit -r "$t" \
        -f txt \
        --severity-level medium \
        --confidence-level medium \
        --skip B101,B601 \
        | tee "$REPORT_DIR/bandit-${name}.txt" || true
done

echo
echo "[bandit] 리포트: $REPORT_DIR/bandit-*.{json,txt}"
exit $EXIT
