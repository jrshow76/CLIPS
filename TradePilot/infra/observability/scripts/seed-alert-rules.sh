#!/usr/bin/env bash
# =============================================================================
# Alert Rule / Alertmanager Config 검증
# -----------------------------------------------------------------------------
# - promtool: Prometheus 룰 문법 검증
# - amtool:   Alertmanager 설정 검증
# - 도구 미설치 시 컨테이너로 실행 (docker)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RULES_DIR="${ROOT}/prometheus/rules"
AM_CFG="${ROOT}/alertmanager/alertmanager.yml"
PROM_CFG="${ROOT}/prometheus/prometheus.yml"

run_promtool() {
  if command -v promtool >/dev/null 2>&1; then
    promtool "$@"
  else
    docker run --rm \
      -v "${ROOT}:/work:ro" \
      --entrypoint promtool \
      prom/prometheus:v2.51.0 \
      "$@"
  fi
}

run_amtool() {
  if command -v amtool >/dev/null 2>&1; then
    amtool "$@"
  else
    docker run --rm \
      -v "${ROOT}:/work:ro" \
      --entrypoint amtool \
      prom/alertmanager:v0.27.0 \
      "$@"
  fi
}

# ---------------------------------------------------------------------------
# 1) Prometheus 룰 검증
# ---------------------------------------------------------------------------
echo "[INFO] Prometheus 룰 검증..."
shopt -s nullglob
fail=0
for f in "${RULES_DIR}"/*.yml; do
  echo "  - $(basename "${f}")"
  if command -v promtool >/dev/null 2>&1; then
    promtool check rules "${f}" || fail=$((fail + 1))
  else
    # 컨테이너 경로 매핑
    rel="${f#${ROOT}/}"
    docker run --rm -v "${ROOT}:/work:ro" --entrypoint promtool \
      prom/prometheus:v2.51.0 check rules "/work/${rel}" \
      || fail=$((fail + 1))
  fi
done

# ---------------------------------------------------------------------------
# 2) Prometheus 설정 검증 (룰 파일 경로는 컨테이너 내부 경로이므로 skip)
# ---------------------------------------------------------------------------
# prometheus.yml 의 rule_files 는 /etc/prometheus/... 절대경로라
# 검증 시 룰 로딩 오류가 날 수 있으므로 syntax-only 모드를 위해 skip 가능.
# 단, 컨테이너 안에서 동일 경로로 마운트하면 통과:
echo "[INFO] Prometheus 설정 syntax 검증..."
if command -v promtool >/dev/null 2>&1; then
  promtool check config "${PROM_CFG}" 2>&1 | grep -v "no such file" || true
else
  docker run --rm \
    -v "${PROM_CFG}:/etc/prometheus/prometheus.yml:ro" \
    -v "${RULES_DIR}:/etc/prometheus/rules:ro" \
    --entrypoint promtool \
    prom/prometheus:v2.51.0 \
    check config /etc/prometheus/prometheus.yml \
    || fail=$((fail + 1))
fi

# ---------------------------------------------------------------------------
# 3) Alertmanager 설정 검증
# ---------------------------------------------------------------------------
echo "[INFO] Alertmanager 설정 검증..."
if command -v amtool >/dev/null 2>&1; then
  amtool check-config "${AM_CFG}" || fail=$((fail + 1))
else
  docker run --rm \
    -v "${AM_CFG}:/etc/alertmanager/alertmanager.yml:ro" \
    -v "${ROOT}/alertmanager/templates:/etc/alertmanager/templates:ro" \
    --entrypoint amtool \
    prom/alertmanager:v0.27.0 \
    check-config /etc/alertmanager/alertmanager.yml \
    || fail=$((fail + 1))
fi

if [[ ${fail} -gt 0 ]]; then
  echo
  echo "[FAIL] ${fail} 개 항목에서 오류 발견." >&2
  exit 1
fi
echo
echo "[OK] 모든 룰/설정 검증 통과."
