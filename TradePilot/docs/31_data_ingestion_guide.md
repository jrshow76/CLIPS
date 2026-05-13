# 31. 데이터 적재 운영 가이드

본 문서는 TradePilot의 시장 데이터 적재 파이프라인 운영 절차를 설명한다.
구현 위치: `backend/app/services/data_ingestion/`, `backend/app/workers/tasks/ingestion_tasks.py`.

---

## 1. 데이터 소스 전략

| 데이터 종류 | 1차 소스 | 보조 소스 | 비고 |
|---|---|---|---|
| 종목 마스터 (KOSPI/KOSDAQ) | pykrx | - | 무료, 인증 불필요 |
| 섹터/업종 매핑 | pykrx (`get_index_portfolio_deposit_file`) | - | KRX 업종지수 코드 기준 |
| 일봉 OHLCV (5년) | pykrx (`get_market_ohlcv_by_date`) | - | 동기 라이브러리 |
| 분봉 OHLCV (최근 90일) | CREON `StockChart` | - | 게이트웨이 가용 시 |
| 시장 지수 (KOSPI/KOSDAQ/KOSPI200) | pykrx (`get_index_ohlcv_by_date`) | - | 코드 1001/2001/1028 |
| 기업 행위 (액면분할/배당) | pykrx + DART OpenAPI(예정) | - | adj_close 산출용 |

**원칙**: CREON 미가용(Linux 본체)에서도 일봉/마스터/섹터/지수 적재가 항상 동작해야 한다. 분봉은 게이트웨이가 살아있을 때만 best-effort로 적재한다.

---

## 2. 적재 주기 (Celery Beat)

`backend/app/workers/celery_app.py` beat schedule 참고. 모두 KST 기준.

| 작업 | Cron | 큐 | 멱등성 |
|---|---|---|---|
| `ingestion.stock_master` | `0 8 * * 1-5` | `ingestion` | YES (UPSERT) |
| `ingestion.daily_prices` | `30 16 * * 1-5` | `ingestion` | YES (UPSERT) |
| `ingestion.market_indices` | `35 16 * * 1-5` | `ingestion` | YES (UPSERT) |
| `ingestion.minute_prices` | `*/5 9-15 * * 1-5` | `ingestion` | YES (UPSERT) |
| `ingestion.ensure_minute_partitions` | `30 23 * * *` | `ingestion` | YES (DDL idempotent) |

워커 실행:

```bash
celery -A app.workers.celery_app worker --loglevel=INFO \
  -Q signals,orders,backtest,ml,notifications,ingestion,default

celery -A app.workers.celery_app beat --loglevel=INFO
```

---

## 3. 초기 데이터 적재 (최초 1회)

### 3.1. 사전 조건
- DB 마이그레이션 완료 (`tp_market` 스키마 + 테이블)
- pykrx 의존성 설치 (`pip install pykrx>=1.0.45`)
- `DATABASE_URL` 환경변수 설정

### 3.2. 실행

호스트에서:
```bash
bash scripts/ingest_initial_data.sh
```

컨테이너 직접 실행:
```bash
docker exec -it tradepilot-backend \
  python /app/scripts/ingest_initial_data.py \
  --start 2021-01-01 --end 2026-05-13
```

부분 실행 옵션:
```bash
# 마스터/지수만 (백필 제외)
python scripts/ingest_initial_data.py --skip-backfill

# 일부 종목만
python scripts/ingest_initial_data.py --codes 005930,000660,035420
```

### 3.3. 예상 소요 시간 (참고)

| 단계 | 데이터 양 | 소요 시간 |
|---|---|---|
| 종목 마스터 + 섹터 | KOSPI~900 + KOSDAQ~1700, 업종 ~50 | 5~10분 |
| 지수 5년 일봉 | 3 지수 × ~1250일 = 3,750행 | <1분 |
| 전 종목 5년 일봉 | ~2,700종목 × 1,250일 ≈ 340만 행 | 60~180분 |

운영 환경에서는 staging에서 1회 측정 후 schedule.

---

## 4. 관리자 API

`/api/v1/admin/ingestion/*` 엔드포인트로 ad-hoc 적재 트리거 가능. 권한: `ROLE_ADMIN` 또는 `ROLE_OPERATOR`.

| Method | Path | 설명 |
|---|---|---|
| POST | `/admin/ingestion/stock-master` | 종목 마스터 즉시 동기화 |
| POST | `/admin/ingestion/daily/{ingest_date}` | 특정일 일봉 적재 |
| POST | `/admin/ingestion/backfill` | 백필 작업 시작 (`{start, end, codes?}`) |
| GET | `/admin/ingestion/jobs` | 진행 중/완료 작업 목록 (Redis) |
| GET | `/admin/ingestion/jobs/{job_id}` | 진행률 조회 |
| POST | `/admin/ingestion/jobs/{job_id}/cancel` | 작업 취소 (best-effort) |

진행률 데이터는 Redis 키 `ingest:job:{job_id}` 와 채널 `ingest:progress` 로 publish된다.

### 예시

```bash
# 1) 백필 트리거
curl -X POST $API/api/v1/admin/ingestion/backfill \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start": "2025-01-01", "end": "2025-12-31"}'
# → {"success": true, "data": {"job_id": "abc...", "status": "QUEUED"}}

# 2) 진행률 조회
curl $API/api/v1/admin/ingestion/jobs/abc... \
  -H "Authorization: Bearer $TOKEN"
# → {"success": true, "data": {"pct": 42, "status": "RUNNING", ...}}
```

---

## 5. 장애 시 복구 절차

### 5.1. 증상별 대응

| 증상 | 확인 | 조치 |
|---|---|---|
| 일봉 누락 (전일 데이터 없음) | `data_consistency_check.sql` §9 | 관리자 API로 해당일 재적재 |
| 종목 갭 (>2일 연속 누락) | §10 | `backfill` API로 부분 백필 |
| 거래량 0 비율 >5% | §11 | pykrx 응답 검증, 휴장일 매핑 확인 |
| 분봉 INSERT 실패 (파티션 없음) | §12 | `ingestion.ensure_minute_partitions` 즉시 실행 |
| 지수 누락 | §13 | `ingestion.market_indices` 재실행 |
| pykrx rate limit | 워커 로그 `pykrx_retry` | `INGEST_PYKRX_SLEEP_SEC` 상향 |

### 5.2. 부분 재적재 (특정 종목·기간)

```bash
curl -X POST $API/api/v1/admin/ingestion/backfill \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "start": "2025-12-01",
    "end": "2025-12-31",
    "codes": ["005930", "000660"]
  }'
```

### 5.3. pykrx 호출 실패

- 자동 재시도: 최대 3회 지수 백오프 (`config.max_retries`).
- 그래도 실패 시: `BackfillResult.failed_codes` 에 누적, 알림 채널로 전송.
- 수동 재시도: 위 백필 API에서 `codes` 인자에 실패 종목만 전달.

---

## 6. 데이터 보관 정책

| 테이블 | 보관 기간 | 다운샘플링 |
|---|---|---|
| `price_daily` | 5년 | - |
| `price_minute` (1분) | 90일 (`INGEST_MINUTE_RETENTION_DAYS`) | 그 이전은 5분봉 → 일봉으로 다운샘플링 권장 |
| `price_minute` (5분 이상) | 5년 | - |
| `market_index_daily` | 무제한 | - |
| `corporate_actions` | 무제한 | - |

분봉 정리는 별도 cron 또는 파티션 DROP으로 수행:
```sql
DROP TABLE IF EXISTS tp_market.price_minute_y2024m05;
```

---

## 7. 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `INGEST_USE_SYNTHETIC` | `false` | true일 때 pykrx 호출 없이 합성 데이터 (CI 용) |
| `INGEST_CHUNK_SIZE` | `1000` | DB UPSERT 청크 크기 |
| `INGEST_PYKRX_SLEEP_SEC` | `0.2` | pykrx 호출 간 sleep |
| `INGEST_MAX_RETRIES` | `3` | pykrx 재시도 횟수 |
| `INGEST_RETRY_BACKOFF_BASE` | `2.0` | 백오프 base (sec) |
| `INGEST_RETRY_BACKOFF_MAX` | `30.0` | 백오프 상한 (sec) |
| `INGEST_MINUTE_RETENTION_DAYS` | `90` | 1분봉 보관 일수 |
| `INGEST_ACTIVE_CODES_LIMIT` | `500` | 장중 분봉 적재 대상 종목 상한 |
| `INGEST_PARTITION_LOOKAHEAD_MONTHS` | `2` | 분봉 파티션 사전 생성 개월 수 |

---

## 8. pykrx Rate Limit 주의사항

- pykrx는 KRX 정보데이터시스템을 스크래핑하므로 과도한 호출 시 차단 가능.
- 권장 sleep: 종목당 0.2초 이상.
- 백필처럼 대량 호출 시: 단일 워커로 직렬 실행 (`-c 1`).
- 차단 의심 시: 1시간 이상 대기 후 재시도, IP 우회보다 sleep 상향이 안전.

---

## 9. 모니터링

### 9.1. 메트릭 (권장 추가)

- `ingestion_upserted_total{type, source}` Counter
- `ingestion_invalid_total{type}` Counter
- `ingestion_duration_seconds{task}` Histogram
- `ingestion_failed_codes_total{task}` Counter

### 9.2. 로그 키 (structlog)

- `pykrx_retry` `pykrx_failed`
- `stocks_upserted` `stock_sectors_upserted`
- `price_daily_upserted` `price_minute_upserted`
- `market_index_daily_upserted`
- `creating_partition`
- `backfill_started` `backfill_finished` `backfill_code_failed`

### 9.3. 알림

- `*_failed` 로그 발생 시 Slack/이메일.
- 일일 16:30 정합성 체크 결과 1건 이상 → 즉시 알림.

---

## 10. 테스트

```bash
# 단위 테스트
pytest backend/tests/unit/test_data_ingestion.py -v

# 통합 테스트 (DB 필요)
pytest backend/tests/integration/test_ingestion_admin.py -v
```

CI에서는 `INGEST_USE_SYNTHETIC=true` 로 pykrx 의존성 없이 테스트.
