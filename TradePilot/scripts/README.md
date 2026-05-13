# TradePilot 운영 스크립트

본 디렉토리는 일일 운영, LIVE 전환 점검, CREON 연결 검증, DB 정합성 점검 등에 사용되는 자동화 스크립트를 포함한다.

| 파일 | 용도 | 실행 주기 |
|---|---|---|
| `daily_health_check.sh` | 게이트웨이/백엔드/Redis/디스크/백업 종합 점검 | 매일 08:10, 16:30 |
| `prelive_smoketest.sh` | LIVE 전환 직전 종합 점검 (6단계) | LIVE 전환 직전 1회 |
| `creon_connect_test.py` | 게이트웨이 연결 + 단순 주문 검증 (모의투자) | Stage 1/2 셋업 시 |
| `data_consistency_check.sql` | DB 정합성 점검 SQL 모음 | 매일 16:30 |
| `ingest_initial_data.py` | 종목 마스터/섹터/지수/일봉 5년 초기 적재 | 최초 1회 (재실행 멱등) |
| `ingest_initial_data.sh` | 위 스크립트의 docker exec 래퍼 | 동일 |

---

## 사용법

### 1. daily_health_check.sh

```bash
# 환경변수 설정
export GATEWAY_URL=http://localhost:9100
export CREON_GATEWAY_API_KEY=your-key
export BACKEND_URL=http://localhost:8000
export REDIS_URL=redis://localhost:6379/0
export BACKUP_DIR=/var/backups/tradepilot

# 실행
./scripts/daily_health_check.sh

# 종료 코드: 0=정상, 1=경고, 2=Critical
```

### 2. prelive_smoketest.sh

```bash
export ADMIN_PW=...
./scripts/prelive_smoketest.sh admin@tradepilot.local

# 모든 항목 PASS 시 LIVE 전환 후보. PM/DevLead 사인오프 필요.
```

### 3. creon_connect_test.py

```bash
# 모의투자 환경에서 1주 매수 주문 검증
python3 scripts/creon_connect_test.py \
    --url http://gateway:9100 \
    --api-key YOUR_KEY \
    --code 005930

# 조회만 (실제 주문 X)
python3 scripts/creon_connect_test.py \
    --url http://gateway:9100 \
    --api-key YOUR_KEY \
    --dry-run
```

### 4. data_consistency_check.sql

```bash
psql $DATABASE_URL -v ON_ERROR_STOP=1 -f scripts/data_consistency_check.sql

# 결과: 모든 쿼리가 0건이어야 정상
# 1건 이상 → 즉시 RCA + 알림
```

### 5. ingest_initial_data.py

최초 1회 실행하여 5년치 시장 데이터를 일괄 적재한다. 모든 적재는 멱등(UPSERT)이므로 재실행해도 안전하다.

```bash
# 컨테이너 외부 (호스트)
bash scripts/ingest_initial_data.sh

# 컨테이너 내부 직접 실행
docker exec -it tradepilot-backend python /app/scripts/ingest_initial_data.py

# 일부 옵션
python scripts/ingest_initial_data.py --start 2021-01-01 --end 2026-05-13
python scripts/ingest_initial_data.py --skip-backfill         # 마스터/지수만
python scripts/ingest_initial_data.py --codes 005930,000660   # 일부 종목만

# 환경변수
DATABASE_URL=postgresql+asyncpg://...
INGEST_USE_SYNTHETIC=true   # pykrx 미설치 환경(CI 등)에서 합성 데이터 사용
```

소요 시간 (참고):
- 종목 마스터 + 섹터: 5~10분
- 지수 5년 일봉: 1분 미만
- 전 종목 5년 일봉 백필: 약 60~180분 (네트워크/CPU/Rate Limit 의존)

---

## 자동화 권장

### Cron (Linux)
```cron
# 매일 08:10 헬스 체크 (장 시작 50분 전)
10 8 * * 1-5 /opt/tradepilot/scripts/daily_health_check.sh >> /var/log/tradepilot/health.log 2>&1

# 매일 16:30 정합성 체크
30 16 * * 1-5 psql $DATABASE_URL -f /opt/tradepilot/scripts/data_consistency_check.sql >> /var/log/tradepilot/consistency.log 2>&1
```

### 결과 알림
- 실패 시 PM/DevLead에게 이메일.
- Critical 실패는 SMS 발송 (옵션).

---

## 보안

- 모든 스크립트는 비밀을 환경변수에서만 읽는다. 평문 하드코딩 금지.
- `data_consistency_check.sql` 의 결과에 PII가 포함될 수 있으므로 로그 파일 NTFS/POSIX 권한 제한.
- LIVE 전환 직전에만 `prelive_smoketest.sh` 실행. 사용 후 토큰은 즉시 폐기.
