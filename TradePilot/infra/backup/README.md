# TradePilot 백업/복구 인프라

PostgreSQL 백업·복구 자동화 + 복구 리허설 시스템.

| 문서 | 위치 |
|---|---|
| 운영 가이드 (필독) | [`/docs/42_backup_recovery_guide.md`](../../docs/42_backup_recovery_guide.md) |
| 운영 런북 | [`/docs/30_operations_runbook.md`](../../docs/30_operations_runbook.md) |

## 디렉토리 구조

```
infra/backup/
├── README.md                          # (본 문서)
├── .env.backup.example                # 환경변수 템플릿
├── lib/
│   └── common.sh                      # 공통 라이브러리(로그/락/암호화/Redis)
├── backup_full.sh                     # 풀백업 (pg_dump -Fc -Z9)
├── backup_wal.sh                      # WAL 아카이빙 (archive_command)
├── backup_logical.sh                  # 글로벌 객체(ROLE/ACL) 백업
├── restore_full.sh                    # 풀백업 복구 (pg_restore)
├── restore_pitr.sh                    # PITR (시점 복구)
├── restore_table.sh                   # 단일 테이블 복구
├── restore_drill.sh                   # 자동 복구 리허설 (매주 일요일)
├── drill_validation.sql               # 리허설 검증 SQL
├── retention.sh                       # 보존 정책 (로컬 7일, S3 라이프사이클)
├── monitor.py                         # 백업 헬스 모니터링
├── s3_upload.sh                       # aws-cli/rclone 업로드 래퍼
├── s3_lifecycle.json                  # S3 라이프사이클 정책 JSON
├── postgresql.conf.snippet            # WAL/archive 설정 스니펫
├── pg_hba.conf.snippet                # 백업/복제 인증 설정
├── crontab.sample                     # 호스트 cron 등록 샘플
├── crontab.supercronic                # 컨테이너용 cron
├── entrypoint.sh                      # 컨테이너 엔트리포인트
├── Dockerfile.backup                  # 백업 사이드카 이미지
├── docker-compose.backup.yml          # 백업 컨테이너 compose
├── systemd/
│   ├── tradepilot-backup.service      # 풀백업 systemd 유닛
│   ├── tradepilot-backup.timer        # 매일 03:00
│   ├── tradepilot-drill.service       # 리허설 systemd 유닛
│   └── tradepilot-drill.timer         # 매주 일요일 04:00
└── tests/
    ├── README.md                      # bats 테스트 안내
    └── test_backup_scripts.bats       # 단위 테스트
```

## 빠른 시작

### 1. 환경변수 설정

```bash
cp .env.backup.example /etc/tradepilot/.env.backup
chmod 0600 /etc/tradepilot/.env.backup
vim /etc/tradepilot/.env.backup    # DB 비밀번호, S3 키, GPG 수신자 입력
```

### 2. 호스트에서 단일 실행

```bash
export BACKUP_ENV_FILE=/etc/tradepilot/.env.backup

# 풀백업 한 번
./backup_full.sh --no-upload

# 복구 리허설 (수동)
./restore_drill.sh --keep-db

# 모니터링
python3 monitor.py
```

### 3. cron 등록

```bash
sudo cp crontab.sample /etc/cron.d/tradepilot-backup
sudo chmod 0644 /etc/cron.d/tradepilot-backup
```

### 4. 또는 systemd timer

```bash
sudo cp systemd/* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tradepilot-backup.timer tradepilot-drill.timer
sudo systemctl list-timers | grep tradepilot
```

### 5. 또는 Docker 사이드카

```bash
docker compose -f docker-compose.backup.yml up -d
docker logs -f tp-backup
```

### 6. PostgreSQL 설정 적용 (필수)

```bash
# 운영 PG 의 postgresql.conf 끝에 스니펫 내용 추가
cat postgresql.conf.snippet >> $PGDATA/postgresql.conf
cat pg_hba.conf.snippet     >> $PGDATA/pg_hba.conf

# 재시작 (wal_level 변경)
docker compose restart postgres
```

### 7. S3 라이프사이클 적용

```bash
aws s3api put-bucket-lifecycle-configuration \
    --bucket tradepilot-backup-prod \
    --lifecycle-configuration file://s3_lifecycle.json
```

## 모니터링 채널 (Redis pub/sub)

| 채널 | 용도 | 페이로드 예시 |
|---|---|---|
| `tp:backup.event` | 백업/리허설 진행 알림 | `{"status":"success","kind":"full","extra":{...}}` |
| `tp:backup.alerts` | CRITICAL/WARN 알림 | `{"severity":"CRITICAL","message":"..."}` |

알림 시스템(이메일/Slack/Telegram) 은 위 채널을 SUBSCRIBE.

## 테스트

```bash
apk add bats        # 또는 apt install bats
bats tests/test_backup_scripts.bats
```

## 문제 해결

| 증상 | 우선 확인 |
|---|---|
| `monitor.py` CRITICAL | `cat .last_full_success` 시간 확인 |
| 락 파일 잔존 | `ls -la /var/backup/tradepilot/.lock/` 후 좀비 PID 삭제 |
| GPG 암호화 실패 | `gpg --list-keys` 로 수신자 키 import 여부 확인 |
| WAL 적체 | `archive_command` 직접 실행 후 stderr 분석 |

자세한 트러블슈팅: [42_backup_recovery_guide.md §9](../../docs/42_backup_recovery_guide.md)
