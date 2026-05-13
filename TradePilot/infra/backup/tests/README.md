# TradePilot 백업 스크립트 테스트

본 디렉토리는 백업/복구 스크립트의 단위 테스트를 담는다.
프레임워크는 [bats-core](https://github.com/bats-core/bats-core) (Bash Automated Testing System).

## 사전 설치

### Ubuntu / Debian
```bash
sudo apt update && sudo apt install -y bats
```

### Alpine (백업 컨테이너)
```bash
apk add --no-cache bats
```

### macOS
```bash
brew install bats-core
```

## 실행

```bash
# 전체 테스트
bats tests/test_backup_scripts.bats

# 특정 테스트만 (필터)
bats -f "retention" tests/test_backup_scripts.bats

# TAP 출력
bats --tap tests/test_backup_scripts.bats

# CI/CD 용
bats --formatter junit tests/test_backup_scripts.bats > /tmp/bats-junit.xml
```

## 테스트 분류

| 분류 | 대상 | 검증 내용 |
|---|---|---|
| common | `lib/common.sh` | 환경변수, 락, 체크섬, 사이즈 변환 |
| full | `backup_full.sh` | --help, --dry-run |
| logical | `backup_logical.sh` | 환경변수 검증 |
| wal | `backup_wal.sh` | 인자 처리, idempotent, gzip |
| restore | `restore_full.sh` | 운영 DB 보호, 파일 검증 |
| s3 | `s3_upload.sh` | 인자, 파일 존재 |
| monitor | `monitor.py` | OK/CRITICAL 판정, JSON 출력 |
| retention | `retention.sh` | 7일 이전 삭제, dry-run 보호 |

## 테스트 격리

각 `setup()` 에서 `$BATS_TEST_TMPDIR` 기반 임시 디렉토리를 만들어
`BACKUP_LOCAL_DIR`, `LOCK_DIR`, `LOG_DIR` 을 모두 격리한다.

`teardown()` 에서 항상 정리되므로 호스트 환경 오염 없음.

## 통합 테스트(추후)

실제 PostgreSQL 컨테이너를 띄워 end-to-end 검증하는 통합 테스트는
`tests/integration/` 디렉토리에 별도 추가 예정 (docker-compose 기반).
샘플:
```bash
# 통합 테스트 (수동)
docker compose -f docker-compose.test.yml up -d postgres
sleep 10
./backup_full.sh --no-upload
./restore_drill.sh --backup-file /var/backup/tradepilot/full/*.dump
docker compose -f docker-compose.test.yml down
```

## CI 통합

`.github/workflows/backup-tests.yml` 에서 PR 마다 자동 실행 권장:
```yaml
# 예시 (실제 추가는 별도 작업)
- name: Run bats tests
  run: bats infra/backup/tests/test_backup_scripts.bats
```
