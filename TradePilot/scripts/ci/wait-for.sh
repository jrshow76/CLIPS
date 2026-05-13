#!/usr/bin/env bash
# wait-for.sh - 호스트:포트 가 LISTEN 될 때까지 대기.
#
# 사용:   wait-for.sh <host> <port> [timeout_sec=60]
# 예:     wait-for.sh localhost 5432 60
# 종료:   0=정상 / 1=타임아웃
#
# bash 의 /dev/tcp 기능만 사용 (외부 도구 불필요).

set -euo pipefail

host="${1:?host 인자가 필요합니다}"
port="${2:?port 인자가 필요합니다}"
timeout="${3:-60}"

start_ts=$(date +%s)
deadline=$((start_ts + timeout))

echo "[wait-for] ${host}:${port} 대기 (timeout=${timeout}s)"

while true; do
  now=$(date +%s)
  if [ "$now" -ge "$deadline" ]; then
    echo "[wait-for] 실패: ${host}:${port} 타임아웃" >&2
    exit 1
  fi

  # /dev/tcp 로 비파괴 연결 시도
  if (exec 3<>"/dev/tcp/${host}/${port}") 2>/dev/null; then
    exec 3<&-
    exec 3>&-
    elapsed=$((now - start_ts))
    echo "[wait-for] OK: ${host}:${port} (${elapsed}s)"
    exit 0
  fi

  sleep 2
done
