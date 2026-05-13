# TradePilot 백업/복구 가이드

> 문서 ID: 42_BACKUP_RECOVERY_GUIDE
> 버전: v1.0
> 작성자: DBA
> 검토자: DevLead, BackendSenior, PM
> 최종 수정일: 2026-05-13

본 문서는 TradePilot PostgreSQL 데이터베이스의 **백업·복구 정책**, **자동화 스크립트 운영법**, **재해 복구 시나리오**, **리허설 절차**, **보안/감사 가이드라인**을 정의한다.

본 문서는 [30_operations_runbook.md](./30_operations_runbook.md) 6장 백업/복구 절을 확장한 상세본이며, 운영 담당자(DBA / DevLead / BackendSenior)는 본 문서를 출력하여 항상 비치한다.

---

## 1. 목표 (RPO / RTO)

| 지표 | 목표 | 근거 |
|---|---|---|
| **RPO** (복구 지점 목표) | **5분** | WAL 아카이빙 `archive_timeout=300s` 기반 |
| **RTO** (복구 시간 목표) | **30분** | 풀백업 복원(15분) + WAL 재생(10분) + 검증(5분) |
| **장애 발견 → 알림** | 1분 이내 | `monitor.py` 가 15분 주기, Redis publish 즉시 |
| **리허설 주기** | 매주 일요일 04:00 | 자동 + 실패 시 CRITICAL 알림 |
| **백업 무결성 검증** | 매 백업마다 SHA256 + 매주 복원 검증 | 양쪽 모두 자동화 |

---

## 2. 백업 종류 (3가지)

### 2.1 풀백업 (Full Backup)

| 항목 | 값 |
|---|---|
| 도구 | `pg_dump -Fc -Z9` (custom format, gzip 9) |
| 주기 | 매일 03:00 KST |
| 보존 | 로컬 7일, S3 30일, 월말 본 1년 |
| 보관 | 로컬 → S3 → (자동 STANDARD_IA → GLACIER → DEEP_ARCHIVE) |
| 암호화 | GPG (`GPG_RECIPIENT`) 또는 age (`AGE_RECIPIENT`) |
| 무결성 | SHA256 체크섬 동시 생성/업로드 |
| 스크립트 | [`infra/backup/backup_full.sh`](../infra/backup/backup_full.sh) |
| 예상 크기 | 50GB (100% 압축률 가정) → 압축 후 10~15GB |

### 2.2 WAL 아카이빙 (Point-In-Time Recovery)

| 항목 | 값 |
|---|---|
| 도구 | PostgreSQL `archive_command` → `backup_wal.sh` |
| 주기 | 5분(`archive_timeout=300s`) 또는 16MB WAL 가득 시 |
| 보존 | 로컬 8일, S3 30일 |
| 무결성 | gzip 압축 + SHA256 |
| 스크립트 | [`infra/backup/backup_wal.sh`](../infra/backup/backup_wal.sh) |
| 효과 | **임의 시점**으로 복구 가능 (5분 단위) |

### 2.3 논리 백업 (Globals)

| 항목 | 값 |
|---|---|
| 도구 | `pg_dumpall --globals-only` |
| 주기 | 매일 02:50 KST (풀백업 10분 전) |
| 대상 | ROLE, TABLESPACE, ACL (DB와 별개) |
| 용도 | 신규 클러스터 재구축 시 권한 일괄 복원 |
| 스크립트 | [`infra/backup/backup_logical.sh`](../infra/backup/backup_logical.sh) |

---

## 3. 일일 운영 절차

### 3.1 자동 작업 타임라인

| 시각 (KST) | 작업 | 실행 방식 |
|---|---|---|
| 매시 5분 | 보존 정책 적용(`retention.sh`) | cron |
| 매 15분 | 백업 모니터링(`monitor.py`) | cron |
| 02:50 | 논리 백업(`backup_logical.sh`) | cron |
| 03:00 | 풀백업(`backup_full.sh`) | cron 또는 systemd timer |
| 매 5분 (자동) | WAL 아카이빙 | PostgreSQL archive_command |
| 일요일 04:00 | 복구 리허설(`restore_drill.sh`) | cron 또는 systemd timer |
| 매월 1일 ~ 3일 | 월말 본 S3 monthly/ 로 승격 | retention.sh 내부 로직 |

### 3.2 운영자 매일 확인 (3분)

```bash
# 1. 백업 헬스 한번에
python3 /opt/tradepilot/infra/backup/monitor.py

# 2. 마지막 백업 파일 크기/시간 (이상 변동 감지)
ls -lh /var/backup/tradepilot/full/ | tail -10

# 3. WAL 적체 여부 (1만개 넘으면 archive_command 실패 의심)
ls /var/backup/tradepilot/wal/ | wc -l

# 4. Redis 알림 확인 (지난 24시간)
redis-cli -u $REDIS_URL XREAD COUNT 50 STREAMS tp:backup.alerts 0
```

### 3.3 운영자 매주 확인 (10분)

- [ ] 일요일 리허설 결과 확인 (`monitor.py` 또는 `tp:backup.event` 채널)
- [ ] S3 버킷 사용량 점검 (`aws s3 ls --summarize --recursive s3://tradepilot-backup-prod/`)
- [ ] 디스크 사용률 < 80% (`df -h /var/backup`)
- [ ] GPG 키 만료일 확인 (`gpg --list-keys --keyid-format LONG`)

---

## 4. 재해 복구 시나리오 (5종)

### 시나리오 1: 단일 테이블 손상 (예: `tp_trade.orders` 일부 행 깨짐)

**증상**: 특정 테이블 SELECT 시 `ERROR: invalid page in block`

**복구 절차** (RTO 15분):
```bash
# 1) 임시 DB로 해당 테이블만 복원
./restore_table.sh /var/backup/tradepilot/full/tradepilot_$(date +%Y%m%d)*.dump.gpg \
                   tp_trade.orders \
                   --target-db tp_orders_recover

# 2) 손상 행 식별 + 임시 DB 에서 재추출
psql -d tradepilot -c "SELECT id FROM tp_trade.orders WHERE ctid IS NULL;" > corrupt_ids.txt

# 3) 운영 DB 에 INSERT (UPSERT)
psql -d tradepilot <<SQL
  INSERT INTO tp_trade.orders
  SELECT * FROM dblink('dbname=tp_orders_recover', 'SELECT * FROM tp_trade.orders WHERE id IN (...)')
  AS t(LIKE tp_trade.orders)
  ON CONFLICT (id) DO UPDATE SET ...;
SQL

# 4) 정합성 점검
psql -d tradepilot -f scripts/data_consistency_check.sql

# 5) 임시 DB DROP
psql -c "DROP DATABASE tp_orders_recover;"
```

---

### 시나리오 2: 전체 DB 손실 (디스크 장애, 클러스터 파괴)

**증상**: postgres 컨테이너 기동 실패, PGDATA 손상

**복구 절차** (RTO 30분):
```bash
# 1) 신규 PGDATA 준비 (다른 디스크/볼륨)
docker volume create tp-postgres-data-new
docker compose down postgres

# 2) 글로벌 객체 먼저 적용 (ROLE/ACL)
psql -h <new_host> -U postgres -d postgres \
     -f /var/backup/tradepilot/logical/globals_$(date +%Y%m%d)*.sql

# 3) 풀백업 + PITR 로 가장 가까운 시점까지 복구
./restore_pitr.sh \
    --base /var/backup/tradepilot/basebackup/latest \
    --wal-dir /var/backup/tradepilot/wal \
    --target-time "$(date -d '5 minutes ago' '+%Y-%m-%d %H:%M:%S KST')" \
    --pgdata /var/lib/postgresql/data

# 4) 검증 (drill_validation.sql)
psql -d tradepilot -f infra/backup/drill_validation.sql

# 5) 애플리케이션 재시작
docker compose up -d
```

---

### 시나리오 3: 데이터센터 장애 (호스트 자체 다운)

**증상**: 운영 호스트 응답 없음, 네트워크 단절

**복구 절차** (RTO 60분, 다른 리전 신규 호스트 가정):
```bash
# 1) 신규 호스트 프로비저닝 (Terraform/Ansible)
# 2) Docker + 백업 컨테이너 설치
git clone <repo> /opt/tradepilot
cd /opt/tradepilot
cp infra/backup/.env.backup.example /etc/tradepilot/.env.backup
# 자격증명, GPG 키 복원

# 3) S3 에서 최신 백업 다운로드 (GPG 키 필요)
aws s3 cp s3://tradepilot-backup-prod/tradepilot/postgres/full/ \
          /var/backup/tradepilot/full/ --recursive

# 4) PITR 시도 (현 시점 -10분 등 보수적 목표)
./restore_pitr.sh --base /var/backup/.../basebackup --wal-dir ... \
                  --target-time "$(date -d '10 minutes ago' '+%Y-%m-%d %H:%M:%S')"

# 5) DNS/로드밸런서 신규 호스트로 전환
# 6) 사용자 통보 + Kill Switch 해제
```

---

### 시나리오 4: 부분 데이터 오염 (배치 잘못 실행, 마이그레이션 오류)

**증상**: 일부 테이블의 값이 일괄 잘못 변경됨 (예: `daily_pnl` 컬럼 오염)

**복구 절차** (RTO 20분, PITR로 직전 시점 복구):
```bash
# 1) 영향 범위 파악
psql -c "SELECT COUNT(*) FROM tp_trade.daily_pnl WHERE updated_at > '<incident_start>';"

# 2) 전용 임시 DB 에 PITR 복구 (사고 1분 전 시점)
./restore_pitr.sh \
    --base /var/backup/tradepilot/basebackup/today \
    --wal-dir /var/backup/tradepilot/wal \
    --target-time '<incident_start - 1 minute>' \
    --pgdata /tmp/tp_recover \
    --port 5433

# 3) 임시 DB 와 운영 DB 비교 후 영향 행만 추출
psql -p 5433 -d tradepilot -c "COPY (SELECT * FROM tp_trade.daily_pnl WHERE date='2026-05-13') TO STDOUT" > recovered.csv

# 4) 운영 DB UPDATE (트랜잭션, 백업)
psql -d tradepilot <<SQL
BEGIN;
CREATE TABLE tp_trade.daily_pnl_oops AS SELECT * FROM tp_trade.daily_pnl WHERE date='2026-05-13';
DELETE FROM tp_trade.daily_pnl WHERE date='2026-05-13';
\COPY tp_trade.daily_pnl FROM 'recovered.csv';
-- 검증 후 COMMIT
COMMIT;
SQL

# 5) 임시 클러스터 정리
pg_ctl -D /tmp/tp_recover stop
rm -rf /tmp/tp_recover
```

---

### 시나리오 5: 의도적/실수 삭제 (DROP TABLE, DELETE)

**증상**: 누군가 `DROP TABLE tp_trade.fills_y2026m05` 실행

**복구 절차** (RTO 25분):
```bash
# 1) 즉시 자동매매 정지 (Kill Switch)
psql -d tradepilot -c "UPDATE users SET auto_trade_enabled=false;"

# 2) 사고 시각 정확히 파악 (Audit Log + PostgreSQL log)
grep "DROP TABLE" /var/log/postgresql/*.log

# 3) 시나리오 4 와 동일하게 PITR (사고 1분 전 시점)
# 4) 임시 DB 에서 해당 테이블만 운영으로 INSERT
# 5) 사고 원인 분석 (감사 로그 + RBAC 검토)

# 사후 조치 (필수):
# - 해당 사용자 권한 검토 및 강등
# - psql 직접 접근 차단 (bastion/audit 강제)
# - DROP/TRUNCATE 차단을 위한 EVENT TRIGGER 추가
```

---

## 5. PITR 복구 단계별 명령

### 5.1 사전 준비

```bash
# 베이스 백업이 없다면 (현재는 풀백업이 베이스 역할)
# 별도 pg_basebackup 도 권장:
pg_basebackup -h <host> -U backup_user -D /var/backup/tradepilot/basebackup/$(date +%Y%m%d) \
              -Ft -z -P --wal-method=stream
```

### 5.2 PITR 실행 (시점 지정)

```bash
./restore_pitr.sh \
    --base /var/backup/tradepilot/basebackup/20260513 \
    --wal-dir /var/backup/tradepilot/wal \
    --target-time '2026-05-13 14:30:00 KST' \
    --pgdata /tmp/tp_pitr_pgdata \
    --port 5433 \
    --yes
```

### 5.3 복구 진행 모니터링

```bash
# 복구 진행 LSN
psql -h localhost -p 5433 -d postgres -c "
  SELECT pg_is_in_recovery(),
         pg_last_wal_replay_lsn(),
         now() - pg_last_xact_replay_timestamp() AS lag;
"

# 복구 로그
tail -f /tmp/tp_pitr_pgdata/log/startup.log
```

### 5.4 검증 + Promote

```bash
# 1) 데이터 검증
psql -h localhost -p 5433 -d tradepilot -f infra/backup/drill_validation.sql

# 2) 검증 OK → promote (read-write 모드 전환)
/usr/lib/postgresql/15/bin/pg_ctl -D /tmp/tp_pitr_pgdata promote

# 3) 운영 DB 와 SWAP (위험!) 또는 별도 백업으로 사용
```

---

## 6. 리허설 절차 및 합격 기준

### 6.1 자동 리허설 (매주 일요일 04:00)

```bash
# restore_drill.sh 가 자동 실행하는 단계
# 1. 최신 풀백업 선택 (find -mtime 기준)
# 2. 임시 DB(tradepilot_drill_<stamp>) 생성
# 3. pg_restore 실행
# 4. drill_validation.sql 검증
# 5. 운영 DB 대비 행수 비율 점검 (>= 80%)
# 6. 임시 DB DROP
# 7. tp:backup.event 에 success/failure publish
```

### 6.2 수동 리허설 (즉시)

```bash
# 특정 백업 파일로
/opt/tradepilot/infra/backup/restore_drill.sh \
    --backup-file /var/backup/tradepilot/full/tradepilot_20260513_030000.dump.gpg \
    --keep-db   # 검증 후 DB 보존(디버깅)

# 결과 확인
cat /var/backup/tradepilot/log/drill_validation_*.log | grep -E "FAIL|PASS|WARN"
```

### 6.3 합격 기준

| 항목 | 합격 기준 |
|---|---|
| pg_restore 종료 코드 | 0 |
| drill_validation FAIL 카운트 | 0건 |
| 핵심 테이블 행수 | 운영 DB의 80% 이상 (백업 시점 차이 고려) |
| 복원 소요 시간 | 30분 이내 |
| 총 검증 시간 | 60분 이내 |

### 6.4 실패 시 절차

1. 즉시 PM/DevLead 에게 CRITICAL 알림 (자동)
2. 임시 DB 는 24시간 보존 (디버깅)
3. RCA 작성 (24시간 내)
4. 다음 백업 즉시 강제 실행 (`./backup_full.sh`)
5. 다음 리허설 직접 수동 실행 (1주 대기 X)

---

## 7. 보안

### 7.1 백업 파일 암호화

- **운영 환경 GPG 필수.** `ALLOW_PLAINTEXT_BACKUP=false` (기본).
- 키 관리:
    - GPG 공개키는 `/etc/tradepilot/gnupg/` 에 배포 (백업 컨테이너 마운트)
    - **개인키는 백업 호스트에 두지 않음** (오프라인 보관)
    - 복구 시에만 격리된 환경에서 키 사용
- 키 로테이션: 1년 1회. 새 키 추가 후 30일 유예 → 구 키 폐기

### 7.2 S3 IAM 최소 권한 (예)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BackupWrite",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:PutObjectAcl"],
      "Resource": "arn:aws:s3:::tradepilot-backup-prod/tradepilot/postgres/*"
    },
    {
      "Sid": "BackupList",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::tradepilot-backup-prod"
    },
    {
      "Sid": "BackupReadForRestore",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::tradepilot-backup-prod/tradepilot/postgres/*",
      "Condition": {
        "StringEquals": { "aws:PrincipalTag/role": "restore-operator" }
      }
    }
  ]
}
```

### 7.3 감사 로그

- 백업 이벤트 → Redis `tp:backup.event`
- 백업 알림 → Redis `tp:backup.alerts`
- 모든 스크립트 → `/var/backup/tradepilot/log/<script>_<date>.log`
- 복구 작업은 별도 감사: `tp_audit.audit_order_history` 와 동일 정책 (append-only)

### 7.4 backup_user ROLE 권장

```sql
CREATE ROLE backup_user LOGIN PASSWORD '<32자 이상 랜덤>'
  REPLICATION
  NOSUPERUSER NOCREATEDB NOCREATEROLE;

GRANT pg_read_all_data, pg_read_all_settings, pg_read_all_stats
  TO backup_user;
```

---

## 8. 비용 추정 (월간)

| 항목 | 단가 | 용량/사용량 | 월 비용 |
|---|---|---|---|
| S3 STANDARD (현재 + 7일) | $0.023/GB | 300GB | **$6.9** |
| S3 STANDARD_IA (8~30일) | $0.0125/GB | 600GB | **$7.5** |
| S3 GLACIER (31~90일) | $0.004/GB | 1.5TB | **$6.0** |
| S3 DEEP_ARCHIVE (91일+) | $0.00099/GB | 2TB | **$2.0** |
| WAL 아카이브 (STANDARD) | $0.023/GB | 50GB | **$1.2** |
| 데이터 전송(IN) | 무료 | - | $0 |
| 복구 GET 요청 (월 100회) | $0.0004/1000 | - | $0.04 |
| **합계** | | | **$23.6/월** |

> 가정: 일일 풀백업 압축 후 10GB. 실제로는 월말 본 1년 보관 포함 시 $25~30 예상.

---

## 9. 트러블슈팅

| 증상 | 원인 | 조치 |
|---|---|---|
| `archive_command failed` 로그 폭주 | `backup_wal.sh` 의 디스크/권한 오류 | 수동 실행 후 stderr 확인. 수정 후 reload (PG가 자동 재시도) |
| 풀백업 36시간 이상 누락 | cron 비활성, 락 파일 잔존 | `/var/backup/tradepilot/.lock/*.lock` 확인 후 좀비 PID면 삭제 |
| 복구 리허설 매번 행수 부족 | 풀백업이 너무 이른 시각(03:00 이전 데이터만 포함) | 수동으로 16:30 시점 백업 추가 |
| GPG 복호화 실패 | 키링에 개인키 없음 | `gpg --import private.key` (격리된 호스트에서만) |
| S3 업로드 PutObject access denied | IAM 정책 누락 또는 KMS 키 권한 | IAM 정책의 PutObject + (KMS 사용 시 Decrypt/GenerateDataKey) |

---

## 10. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-13 | DBA | 최초 작성 (백업/복구 자동화 + 리허설) |
