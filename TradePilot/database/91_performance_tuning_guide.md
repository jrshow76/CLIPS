# TradePilot DB 성능 튜닝 가이드

> 문서 ID: 91_PERF_TUNING_GUIDE
> 버전: v1.0
> 작성자: DBA
> 최종 수정일: 2026-05-14

본 문서는 운영자(DBA / DevLead / BackendSenior)가 슬로우 쿼리 발생 시
표준 절차에 따라 분석/튜닝/검증할 수 있도록 한다.

---

## 1. 쿼리 튜닝 절차 (Workflow)

### 1.1 식별 단계 — "느린 것을 어떻게 알 것인가?"

| 채널 | 도구 | 활용 |
|---|---|---|
| 슬로우 쿼리 로그 | `log_min_duration_statement = 500ms` | postgresql.log → pgBadger 리포트 |
| 통계 누적 | `pg_stat_statements` 확장 | 평균/최대/호출수 기반 TOP-N |
| 알림 | Prometheus + pg_exporter | `pg_stat_database` 슬로우율 알람 |
| 사용자 신고 | Sentry/Slack | DevLead → DBA 에스컬레이션 |

### 1.2 분석 단계 — EXPLAIN ANALYZE 해석

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT ...
```

확인 포인트:
1. **Plan rows vs Actual rows**: 10배 이상 차이 → `ANALYZE` 또는 통계 강화 필요.
2. **Seq Scan on large table**: 인덱스 누락 또는 통계 왜곡.
3. **Index Scan + Filter(rows removed)**: 부분 인덱스 또는 복합 인덱스 검토.
4. **Sort Method = external merge**: `work_mem` 부족 → 세션 단위 상향.
5. **Bitmap Heap Scan + recheck cond**: 정상이나 행 수 많으면 Index Scan 우선 검토.
6. **Buffers: shared read=N**: 캐시 미스. `pg_statio_user_tables` 보강 후 재실행.
7. **Append (partitioned table)**: 파티션 프루닝 여부 확인. 모든 자식 스캔 시 키 조건 누락.

### 1.3 가설 수립 — "왜 느린가?"

| 패턴 | 가설 | 대책 |
|---|---|---|
| Seq Scan + 작은 결과 | 인덱스 없음 | 인덱스 추가 |
| Index Scan + Filter 큼 | 인덱스 비효율 | 복합/Partial 인덱스 |
| Hash Join → Sort 비용 큼 | work_mem 부족 | `SET work_mem = '64MB'` |
| 파티션 모두 Append | 파티션 키 누락 | 쿼리에 키 조건 추가 |
| 통계 stale | analyze 미실행 | `ANALYZE` 또는 statistics target↑ |
| Lock wait | 동시 UPDATE 충돌 | 트랜잭션 단축, 락 순서 일관화 |

### 1.4 검증 단계

1. 개발 DB(현실 데이터 복제본)에서 인덱스 추가 + ANALYZE
2. `EXPLAIN ANALYZE` 재실행 → 비용/시간 감소 확인
3. 운영 DB는 `CREATE INDEX CONCURRENTLY` 로 적용 (트랜잭션 외부)
4. 적용 후 24시간 모니터링: `pg_stat_user_indexes.idx_scan` 증가 / 쿼리 평균시간 하락

---

## 2. 인덱스 추가/제거 의사결정 트리

```
[쿼리 슬로우 발생]
   │
   ├─ Seq Scan + 작은 selectivity?
   │     ├─ YES → 인덱스 추가 (단일 또는 복합)
   │     │           ├─ 다중 컬럼 WHERE? → 복합 (선택성 높은 컬럼 선두)
   │     │           ├─ 일부 행만 자주 조회? → Partial Index
   │     │           ├─ 전 인덱스 컬럼 외 추가 컬럼 SELECT? → Covering Index (INCLUDE)
   │     │           ├─ 시계열 + 키 조건 없음? → BRIN
   │     │           └─ JSONB 키 검색? → GIN (jsonb_path_ops)
   │     └─ NO → 다음
   │
   ├─ Index Scan + Filter rows removed 큼?
   │     ├─ YES → Partial 또는 복합 인덱스 검토
   │
   ├─ 파티션 모두 스캔?
   │     ├─ YES → 쿼리에 파티션 키 조건 추가 (애플리케이션 수정)
   │
   └─ 통계 오류?
         └─ YES → ANALYZE / STATISTICS↑
```

### 인덱스 추가의 비용

| 측면 | 비용 |
|---|---|
| 디스크 | B-Tree: 테이블 크기의 10~30% (단일 컬럼) |
| INSERT/UPDATE 지연 | 인덱스 1개당 1~5% (대량 적재 시 누적) |
| VACUUM 시간 | 인덱스가 많을수록 vacuum 시간↑ |
| 플래너 계획 시간 | 인덱스 후보가 많으면 plan time 증가 |

→ **읽기/쓰기 트레이드오프**: 인덱스 무한 추가는 금물. 쓰기가 인덱스 비용을 압도하는 테이블(예: `audit_login`)에서는 신중.

### 제거 의사결정

```
[idx_scan = 0 인 인덱스 발견]
   │
   ├─ 운영 30일 이상 유지?
   │     ├─ NO → 보류 (월말 배치/분기 리포트 가능성)
   │     └─ YES → 다음
   │
   ├─ UNIQUE/PK인가?
   │     ├─ YES → 절대 제거 금지
   │     └─ NO → 다음
   │
   ├─ FK 컬럼 단독 인덱스인가?
   │     ├─ YES → 보존(부모 DELETE 시 자식 락 회피)
   │     └─ NO → 제거 후보
   │
   └─ DROP INDEX CONCURRENTLY <name>;
```

---

## 3. 파티셔닝 운영

### 3.1 매월 1일 — 익월 파티션 생성

`scripts/db/create_partition.sh` (별도 운영 스크립트) 또는:

```sql
SELECT * FROM public.fn_ensure_future_partitions(3);
```

- 매주 일요일 02:00 cron 권장
- 결과: created=true 가 있으면 신규 생성됨

### 3.2 매월 25일 — 보관기간 초과 파티션 detach

```sql
-- 분봉 60개월 보관 (5분 이상)
SELECT * FROM public.fn_archive_old_partitions('tp_market','price_minute', 60);
-- 주문/체결 10년
SELECT * FROM public.fn_archive_old_partitions('tp_trade','orders', 120);
SELECT * FROM public.fn_archive_old_partitions('tp_trade','fills',  120);
-- 알림 6개월
SELECT * FROM public.fn_archive_old_partitions('tp_notify','notifications', 6);
-- 감사 10년
SELECT * FROM public.fn_archive_old_partitions('tp_audit','audit_order_history', 120);
```

detach 후 절차:
1. `pg_dump --table=<detached_partition>` → 콜드 스토리지(S3)
2. 백업 검증
3. `DROP TABLE <detached_partition>` (운영자 확인 후)

### 3.3 누락 파티션 감지 (일 1회)

```sql
SELECT * FROM tp_audit.v_missing_partitions WHERE NOT exists;
SELECT * FROM tp_audit.v_default_partition_health WHERE health_status='ALERT';
```

→ `data_consistency_check.sql` 의 18/19번에 포함됨.

### 3.4 파티션 인덱스 정책

- 부모 인덱스 → 자식 자동 전파 (PG11+)
- UNIQUE 제약은 파티션 키 포함 필수
- 멱등성 키처럼 키 미포함 UNIQUE는 `idempotency_key` partial + 애플리케이션 가드

---

## 4. 머터리얼라이즈드 뷰 운영

### 4.1 REFRESH 패턴

| MV | 주기 | 명령 |
|---|---|---|
| `tp_market.mv_sector_daily_summary` | 매일 17:00 KST | `REFRESH MATERIALIZED VIEW CONCURRENTLY ...` |
| `tp_analysis.mv_indicator_summary` | 매일 17:30 KST | 〃 |
| `tp_trade.mv_user_pnl_summary` | 매일 18:00 KST | 〃 |

또는 일괄:
```sql
SELECT * FROM public.fn_refresh_materialized_views(true);
```

### 4.2 CONCURRENTLY 주의사항

- UNIQUE 인덱스 필수 (이미 정의됨)
- REFRESH 중 SELECT 가능, 단 디스크 사용량 일시 2배
- 첫 적재(`WITH NO DATA` 이후)는 반드시 일반 REFRESH 1회

### 4.3 갱신 실패 시 대응

```sql
-- 1) MV 상태 확인
SELECT schemaname, matviewname, ispopulated FROM pg_matviews WHERE schemaname LIKE 'tp_%';
-- 2) ispopulated=false 면 일반 REFRESH (CONCURRENTLY X)
REFRESH MATERIALIZED VIEW tp_market.mv_sector_daily_summary;
```

### 4.4 Stale 데이터 운영 규칙

- MV는 **D-1 기준** 데이터로 운영(장 마감 후 갱신).
- 실시간이 필요한 화면(보유 종목, 미체결 주문)은 MV 사용 금지 → raw 테이블 직접.
- MV 갱신 시각이 사용자에게 노출되는 화면(`업데이트: 2026-05-14 17:00`)에는 명시.

---

## 5. VACUUM / ANALYZE 점검 주기

### 5.1 정기 점검

| 항목 | 주기 | 방법 |
|---|---|---|
| Bloat 비율 | 주 1회 | `tp_audit.v_table_bloat_estimate` |
| Dead tuple 누적 | 일 1회 | `data_consistency_check.sql` #16 |
| Autovacuum 진행 | 실시간 | `pg_stat_progress_vacuum` |
| 통계 stale | 주 1회 | `pg_stat_user_tables.last_analyze` |

### 5.2 수동 VACUUM 시점

- `dead_pct > 20%` 지속
- 대용량 DELETE 직후
- `pg_repack` 설치 시 off-peak 시간대(02:00~04:00 KST)에 수행

```sql
-- 일반(블로킹 적음)
VACUUM (VERBOSE, ANALYZE) tp_trade.orders;
-- 강제(전체 락) - 점검 시간대만
VACUUM FULL tp_trade.orders;  -- 또는 pg_repack 권장
```

### 5.3 ANALYZE 강제

```sql
ANALYZE tp_trade.orders;
ANALYZE tp_trade.fills;
ANALYZE tp_market.price_minute;  -- 파티션 부모 → 자식 통계 동시 갱신
```

### 5.4 Autovacuum 임계값

`migrations/2026_05_autovacuum_tuning.sql` 참조.

| 분류 | scale_factor | 비고 |
|---|---|---|
| 고빈도 UPDATE (orders, positions, signals) | 0.02 ~ 0.05 | 매 2~5% 변경 시 vacuum |
| INSERT-only 시세 | insert_scale_factor=0.05~0.10 | visibility map 갱신 |
| append-only 감사 | insert_scale_factor=0.20 | overhead 최소 |

---

## 6. pg_stat_statements 활성화 가이드

### 6.1 설치

```sql
-- (1) 설정 (postgresql.conf 또는 ALTER SYSTEM)
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.max = 5000;
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET track_activity_query_size = 4096;
-- restart 필요

-- (2) DB 단위 확장 생성
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### 6.2 핵심 쿼리

```sql
-- 평균 실행시간 TOP 20
SELECT LEFT(query, 200) AS q,
       calls,
       ROUND(mean_exec_time::numeric, 2) AS mean_ms,
       ROUND(total_exec_time::numeric, 2) AS total_ms,
       rows
  FROM pg_stat_statements
 WHERE query NOT ILIKE '%pg_%'
 ORDER BY mean_exec_time DESC
 LIMIT 20;

-- 총 누적 시간 TOP 20 (병목 영향력)
SELECT LEFT(query, 200) AS q, calls, total_exec_time, rows
  FROM pg_stat_statements
 ORDER BY total_exec_time DESC
 LIMIT 20;

-- 캐시 히트율 낮은 쿼리
SELECT LEFT(query, 200) AS q,
       calls,
       ROUND((100.0 * shared_blks_hit /
              NULLIF(shared_blks_hit + shared_blks_read, 0))::numeric, 2) AS hit_pct
  FROM pg_stat_statements
 WHERE shared_blks_read > 1000
 ORDER BY hit_pct ASC NULLS LAST
 LIMIT 20;

-- 리셋(주 1회 운영자 결정)
SELECT pg_stat_statements_reset();
```

---

## 7. 인덱스 사용도 모니터링

```sql
-- 모든 인덱스 사용도
SELECT * FROM tp_audit.v_index_usage ORDER BY idx_scan ASC;

-- 미사용 인덱스 (제거 후보)
SELECT * FROM tp_audit.v_index_usage WHERE usage_band = 'UNUSED';

-- 중복 인덱스
SELECT * FROM tp_audit.v_index_duplicates;
```

→ 월 1회 DBA가 검토하고 DevLead 협의 후 정리.

---

## 8. 락 / 트랜잭션 모니터링

### 8.1 실시간 락 대기

```sql
SELECT pid, usename, state, wait_event_type, wait_event,
       LEFT(query, 200) AS query,
       now() - query_start AS duration
  FROM pg_stat_activity
 WHERE wait_event_type = 'Lock';
```

### 8.2 데드락 / 장기 트랜잭션

- `log_lock_waits = on`
- `deadlock_timeout = 1s`
- 10분 이상 진행 트랜잭션 자동 알람 (`data_consistency_check.sql` #22)

### 8.3 행 레벨 락 추적 (PG14+)

```sql
SELECT blocked.pid AS blocked_pid,
       blocked.usename AS blocked_user,
       blocking.pid AS blocking_pid,
       blocking.usename AS blocking_user,
       LEFT(blocked.query, 200) AS blocked_query,
       LEFT(blocking.query, 200) AS blocking_query
  FROM pg_stat_activity blocked
  JOIN pg_stat_activity blocking
       ON blocking.pid = ANY(pg_blocking_pids(blocked.pid));
```

---

## 9. 일일 점검 체크리스트

매일 16:30 (장 마감 30분 후) `scripts/data_consistency_check.sql` 자동 실행 결과를 점검:

- [ ] 부록 A #14: 미사용 인덱스 (월 1회 정리)
- [ ] 부록 A #15: 중복 인덱스 (월 1회 정리)
- [ ] 부록 A #16: Dead tuple 비율 20% 초과 (즉시 VACUUM)
- [ ] 부록 A #17: 슬로우 쿼리 TOP 30 (BackendSenior 공유)
- [ ] 부록 A #18: 누락 파티션 (즉시 생성)
- [ ] 부록 A #19: DEFAULT 파티션 비대화 (ALERT 시 즉시 대응)
- [ ] 부록 A #20: 락 대기 5초 초과 (장 시간대 한정 위험)
- [ ] 부록 A #21: 캐시 히트율 < 99% (shared_buffers 검토)
- [ ] 부록 A #22: 10분 이상 트랜잭션 (애플리케이션 버그 의심)

---

## 10. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | DBA | 최초 작성. 90_QUERY_CATALOG와 함께 도입 |
