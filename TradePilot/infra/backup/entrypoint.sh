#!/usr/bin/env bash
# =====================================================================
# TradePilot 백업 컨테이너 엔트리포인트
# 파일: entrypoint.sh
# 모드:
#   cron       supercronic 으로 crontab.sample 에 따라 자동 실행 (기본)
#   once-full  풀백업 한 번 실행 후 종료
#   once-drill 리허설 한 번 실행 후 종료
#   shell      bash 셸 실행 (디버깅)
# 사용:
#   docker run tradepilot/backup once-full
#   docker run tradepilot/backup cron
# =====================================================================

set -euo pipefail

CMD="${1:-cron}"
SCRIPT_DIR="/opt/tradepilot/infra/backup"

case "${CMD}" in
    cron)
        echo "[entrypoint] supercronic 으로 cron 시작"
        # supercronic용 crontab은 사용자 컬럼이 없는 표준 형식
        # crontab.sample 에서 환경변수/MAILTO 라인 제거하고 사용
        exec supercronic -passthrough-logs "${SCRIPT_DIR}/crontab.supercronic"
        ;;
    once-full)
        echo "[entrypoint] 풀백업 1회 실행"
        exec "${SCRIPT_DIR}/backup_full.sh"
        ;;
    once-logical)
        echo "[entrypoint] 논리 백업 1회 실행"
        exec "${SCRIPT_DIR}/backup_logical.sh"
        ;;
    once-drill)
        echo "[entrypoint] 리허설 1회 실행"
        exec "${SCRIPT_DIR}/restore_drill.sh"
        ;;
    monitor)
        echo "[entrypoint] 모니터링"
        exec python3 "${SCRIPT_DIR}/monitor.py"
        ;;
    shell|bash)
        exec bash
        ;;
    *)
        echo "[entrypoint] 사용법: cron | once-full | once-logical | once-drill | monitor | shell"
        exit 1
        ;;
esac
