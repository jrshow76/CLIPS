#!/usr/bin/env python3
# =====================================================================
# TradePilot 백업 모니터링 스크립트
# 파일: monitor.py
# 목적:
#   백업 시스템의 건강도 점검 → 알림 발송
#   - 24시간 내 풀백업 없음 → CRITICAL
#   - 1시간 내 WAL 아카이브 없음 → WARN
#   - 7일 내 리허설 없음 → WARN
#   - 직전 리허설 실패 → CRITICAL
#   - 디스크 사용률 80% 이상 → WARN
#
# 의존성: python3.9+, redis(optional)
#
# 환경변수:
#   BACKUP_LOCAL_DIR
#   REDIS_URL
#   REDIS_BACKUP_ALERT_CHANNEL (기본 tp:backup.alerts)
#
# 사용법:
#   python3 monitor.py
#   python3 monitor.py --json    # JSON으로 출력
#   python3 monitor.py --no-alert  # 알림 안 보냄(체크만)
#
# Cron 예: */15 * * * * /opt/tradepilot/infra/backup/monitor.py >> /var/log/tradepilot/monitor.log 2>&1
# =====================================================================

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional


# ---- 임계값 ----------------------------------------------------------
THRESHOLD_FULL_BACKUP_HOURS = 24
THRESHOLD_WAL_ARCHIVE_MINUTES = 60
THRESHOLD_DRILL_DAYS = 7
THRESHOLD_DISK_USAGE_PCT = 80


# ---- 데이터 클래스 ---------------------------------------------------
@dataclass
class CheckResult:
    name: str
    status: str            # OK | WARN | CRITICAL
    message: str
    value: Optional[str] = None


# ---- 유틸 -----------------------------------------------------------
def read_marker_file(path: Path) -> Optional[datetime]:
    """마커 파일 첫 줄(ISO8601 UTC) 파싱."""
    if not path.exists():
        return None
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0].strip()
        # 'Z' 접미사 처리
        if first.endswith("Z"):
            first = first[:-1] + "+00:00"
        return datetime.fromisoformat(first)
    except (ValueError, IndexError):
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---- 개별 체크 -------------------------------------------------------
def check_last_full_backup(backup_dir: Path) -> CheckResult:
    marker = backup_dir / ".last_full_success"
    last = read_marker_file(marker)
    if last is None:
        return CheckResult(
            "last_full_backup", "CRITICAL",
            "마지막 풀백업 마커 없음 (한 번도 성공한 적 없음)",
        )
    age = now_utc() - last
    age_hours = age.total_seconds() / 3600
    if age_hours > THRESHOLD_FULL_BACKUP_HOURS:
        return CheckResult(
            "last_full_backup", "CRITICAL",
            f"마지막 풀백업이 {age_hours:.1f}시간 전 (임계 {THRESHOLD_FULL_BACKUP_HOURS}h)",
            value=last.isoformat(),
        )
    return CheckResult(
        "last_full_backup", "OK",
        f"마지막 풀백업: {age_hours:.1f}시간 전",
        value=last.isoformat(),
    )


def check_last_wal_archive(backup_dir: Path) -> CheckResult:
    marker = backup_dir / ".last_wal_archive"
    last = read_marker_file(marker)
    if last is None:
        return CheckResult(
            "last_wal_archive", "WARN",
            "WAL 아카이브 마커 없음 (archive_command 미설정 의심)",
        )
    age = now_utc() - last
    age_minutes = age.total_seconds() / 60
    if age_minutes > THRESHOLD_WAL_ARCHIVE_MINUTES:
        return CheckResult(
            "last_wal_archive", "WARN",
            f"마지막 WAL 아카이브가 {age_minutes:.1f}분 전 (임계 {THRESHOLD_WAL_ARCHIVE_MINUTES}m)",
            value=last.isoformat(),
        )
    return CheckResult(
        "last_wal_archive", "OK",
        f"마지막 WAL 아카이브: {age_minutes:.1f}분 전",
        value=last.isoformat(),
    )


def check_last_drill(backup_dir: Path) -> CheckResult:
    marker = backup_dir / ".last_drill_success"
    last = read_marker_file(marker)
    if last is None:
        return CheckResult(
            "last_drill", "WARN",
            "복구 리허설 한 번도 성공한 적 없음",
        )
    age = now_utc() - last
    age_days = age.total_seconds() / 86400
    if age_days > THRESHOLD_DRILL_DAYS:
        return CheckResult(
            "last_drill", "CRITICAL",
            f"마지막 리허설 {age_days:.1f}일 전 (임계 {THRESHOLD_DRILL_DAYS}d)",
            value=last.isoformat(),
        )
    return CheckResult(
        "last_drill", "OK",
        f"마지막 리허설: {age_days:.1f}일 전",
        value=last.isoformat(),
    )


def check_disk_usage(backup_dir: Path) -> CheckResult:
    if not backup_dir.exists():
        return CheckResult("disk_usage", "WARN", f"백업 디렉토리 없음: {backup_dir}")
    total, used, free = shutil.disk_usage(str(backup_dir))
    pct = used / total * 100 if total > 0 else 0
    free_gb = free / (1024 ** 3)
    if pct >= THRESHOLD_DISK_USAGE_PCT:
        return CheckResult(
            "disk_usage", "WARN",
            f"디스크 사용률 {pct:.1f}% (여유 {free_gb:.1f}GB)",
            value=f"{pct:.1f}%",
        )
    return CheckResult(
        "disk_usage", "OK",
        f"디스크 사용률 {pct:.1f}% (여유 {free_gb:.1f}GB)",
        value=f"{pct:.1f}%",
    )


def check_backup_file_count(backup_dir: Path) -> CheckResult:
    full_dir = backup_dir / "full"
    if not full_dir.exists():
        return CheckResult("backup_files", "CRITICAL", "full/ 디렉토리 없음")
    files = list(full_dir.glob("tradepilot_*.dump*"))
    files = [f for f in files if not f.name.endswith(".sha256")]
    count = len(files)
    if count == 0:
        return CheckResult("backup_files", "CRITICAL", "full/ 에 백업 파일 0개")
    if count == 1:
        return CheckResult(
            "backup_files", "WARN",
            "백업 파일이 1개뿐 (이전 백업 누락 의심)",
            value=str(count),
        )
    return CheckResult(
        "backup_files", "OK",
        f"풀백업 파일 {count}개 보존 중",
        value=str(count),
    )


def check_lock_files_stale(backup_dir: Path) -> CheckResult:
    """1시간 이상 묵은 락은 좀비 프로세스 흔적."""
    lock_dir = backup_dir / ".lock"
    if not lock_dir.exists():
        return CheckResult("stale_locks", "OK", "락 디렉토리 없음(정상)")
    threshold = now_utc() - timedelta(hours=1)
    stale = []
    for lock in lock_dir.glob("*.lock"):
        try:
            mtime = datetime.fromtimestamp(lock.stat().st_mtime, tz=timezone.utc)
            if mtime < threshold:
                stale.append(lock.name)
        except OSError:
            continue
    if stale:
        return CheckResult(
            "stale_locks", "WARN",
            f"오래된 락 파일 {len(stale)}개: {', '.join(stale)}",
            value=str(len(stale)),
        )
    return CheckResult("stale_locks", "OK", "락 파일 정상")


# ---- 알림 발송 -------------------------------------------------------
def publish_redis(channel: str, payload: dict) -> bool:
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return False
    redis_cli = shutil.which("redis-cli")
    if not redis_cli:
        return False
    try:
        msg = json.dumps(payload, ensure_ascii=False)
        subprocess.run(
            [redis_cli, "-u", redis_url, "PUBLISH", channel, msg],
            check=True, capture_output=True, timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def send_alert(severity: str, message: str, results: List[CheckResult]) -> None:
    channel = os.environ.get("REDIS_BACKUP_ALERT_CHANNEL", "tp:backup.alerts")
    payload = {
        "ts": now_utc().isoformat(),
        "severity": severity,
        "source": "monitor.py",
        "message": message,
        "checks": [asdict(r) for r in results],
    }
    publish_redis(channel, payload)


# ---- 메인 -----------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="TradePilot 백업 모니터링")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument("--no-alert", action="store_true", help="알림 발송 생략")
    parser.add_argument("--backup-dir",
                        default=os.environ.get("BACKUP_LOCAL_DIR", "/var/backup/tradepilot"))
    args = parser.parse_args()

    backup_dir = Path(args.backup_dir)
    checks: List[CheckResult] = [
        check_last_full_backup(backup_dir),
        check_last_wal_archive(backup_dir),
        check_last_drill(backup_dir),
        check_disk_usage(backup_dir),
        check_backup_file_count(backup_dir),
        check_lock_files_stale(backup_dir),
    ]

    # 결과 집계
    critical_count = sum(1 for c in checks if c.status == "CRITICAL")
    warn_count = sum(1 for c in checks if c.status == "WARN")

    if args.json:
        out = {
            "ts": now_utc().isoformat(),
            "backup_dir": str(backup_dir),
            "summary": {
                "critical": critical_count,
                "warn": warn_count,
                "ok": len(checks) - critical_count - warn_count,
            },
            "checks": [asdict(c) for c in checks],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"=== TradePilot 백업 모니터링 ({now_utc().isoformat()}) ===")
        print(f"디렉토리: {backup_dir}")
        for c in checks:
            symbol = {"OK": "OK", "WARN": "WARN", "CRITICAL": "CRIT"}.get(c.status, "?")
            print(f"  [{symbol:4}] {c.name:25} {c.message}")
        print(f"--- 요약: CRITICAL={critical_count} WARN={warn_count} OK={len(checks)-critical_count-warn_count}")

    # 알림
    if not args.no_alert:
        if critical_count > 0:
            send_alert("CRITICAL", f"백업 시스템 CRITICAL {critical_count}건", checks)
        elif warn_count > 0:
            send_alert("WARN", f"백업 시스템 경고 {warn_count}건", checks)

    # 종료 코드
    if critical_count > 0:
        return 2
    if warn_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
