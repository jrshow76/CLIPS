# TradePilot 인덱스/파티셔닝/통계 전략

> 문서 ID: 32_INDEX_STRATEGY
> 버전: v1.0
> 작성자: DBA
> 최종 수정일: 2026-05-12

본 문서는 TradePilot 데이터베이스의 인덱스 설계, 파티셔닝 전략, 통계/Vacuum 운영 정책을 정의한다.

---

## 1. 인덱스 설계 원칙

1. **자주 조회되는 컬럼 조합을 우선** (WHERE/JOIN/ORDER BY)
2. **카디널리티(고유도)가 높은 컬럼을 선두에** 배치 (다만 시계열은 시간 컬럼을 후순위로)
3. **외래키 컬럼은 무조건 인덱스 생성** (FK 조인/삭제 성능)
4. **부분 인덱스(Partial Index)** 적극 활용 (status='ACTIVE'처럼 일부만 자주 조회)
5. **커버링 인덱스(`INCLUDE`)** 로 인덱스-온리 스캔 유도
6. **시계열은 BRIN** 우선 검토 (B-Tree 대비 1/1000 크기, 시간 정렬 데이터에 적합)
7. **JSONB는 GIN**, **텍스트 검색은 pg_trgm** 결합
8. 인덱스 추가 전 반드시 `EXPLAIN ANALYZE`로 실행계획 검증

---

## 2. 도메인별 인덱스 카탈로그

### 2.1 사용자 도메인 (`tp_user`)

| 테이블 | 인덱스 | 컬럼 | 종류 | 목적 |
|---|---|---|---|---|
| `users` | `uq_users_email` | `email` | B-Tree UNIQUE | 로그인 |
| `users` | `uq_users_public_id` | `public_id` | B-Tree UNIQUE | 외부 노출 ID 조회 |
| `users` | `idx_users_role` | `role` | B-Tree | 관리 화면 필터 |
| `users` | `idx_users_locked_until` | `locked_until` | B-Tree Partial `WHERE locked_until IS NOT NULL` | 잠금 계정 조회 |
| `sessions` | `uq_sessions_refresh_hash` | `refresh_token_hash` | B-Tree UNIQUE | 토큰 조회 |
| `sessions` | `idx_sessions_user_expires` | `(user_id, expires_at)` | B-Tree | 사용자별 세션 정리 |
| `otp_codes` | `idx_otp_user_purpose` | `(user_id, purpose, expires_at)` | B-Tree | OTP 검증 |
| `otp_codes` | `uq_otp_otp_id` | `otp_id` | B-Tree UNIQUE | OTP_ID 조회 |
| `audit_login` | `idx_audit_login_user_ts` | `(user_id, created_at DESC)` | B-Tree | 사용자별 이력 |
| `audit_login` | `idx_audit_login_created` | `created_at` | BRIN | 기간 스캔 |
| `user_favorites` | (PK) | `(user_id, stock_id)` | B-Tree | 즐겨찾기 조회 |

### 2.2 시장 도메인 (`tp_market`)

| 테이블 | 인덱스 | 컬럼 | 종류 | 목적 |
|---|---|---|---|---|
| `stocks` | `uq_stocks_code` | `code` | B-Tree UNIQUE | 코드 조회 |
| `stocks` | `idx_stocks_market` | `market` | B-Tree | 마켓 필터 |
| `stocks` | `idx_stocks_name_trgm` | `name` | GIN (pg_trgm) | 종목명 검색 |
| `stocks` | `idx_stocks_market_cap` | `market_cap DESC` | B-Tree | 시총 정렬 |
| `sectors` | `uq_sectors_code` | `code` | B-Tree UNIQUE | - |
| `stock_sectors` | `idx_stock_sectors_sector_stock` | `(sector_id, stock_id)` | B-Tree | 섹터→종목 드릴다운 |
| `price_daily` | (PK) | `(stock_id, trade_date)` | B-Tree | 종목별 일자 조회 |
| `price_daily` | `idx_price_daily_date` | `trade_date` | BRIN | 일자 범위 스캔 |
| `price_minute` | (PK) | `(stock_id, ts)` | B-Tree | 종목별 시계열 |
| `price_minute` | `idx_price_minute_ts` | `ts` | BRIN | 시간 범위 |
| `price_minute` | `idx_price_minute_interval` | `(interval_min, stock_id, ts DESC)` | B-Tree | 주기별 차트 |
| `corporate_actions` | `idx_corp_action_stock_date` | `(stock_id, effective_date)` | B-Tree | 종목 액션 조회 |

### 2.3 분석 도메인 (`tp_analysis`)

| 테이블 | 인덱스 | 컬럼 | 종류 | 목적 |
|---|---|---|---|---|
| `indicators_daily` | (PK) | `(stock_id, trade_date)` | B-Tree | 종목 지표 시계열 |
| `indicators_daily` | `idx_ind_daily_rsi_partial` | `trade_date` | B-Tree Partial `WHERE rsi14 < 30` | 과매도 스캐너 |
| `indicators_daily` | `idx_ind_daily_macd_golden` | `trade_date` | B-Tree Partial `WHERE macd > macd_signal` | 골든크로스 |
| `sector_metrics_daily` | (PK) | `(sector_id, trade_date)` | B-Tree | 섹터 시계열 |
| `recommendations` | `idx_reco_date_score` | `(trade_date, score DESC)` | B-Tree | TOP-N 랭킹 |
| `recommendations` | `idx_reco_strategy_date` | `(strategy_id, trade_date)` | B-Tree | 전략별 |
| `recommendations` | `idx_reco_stock` | `stock_id` | B-Tree | 종목별 |
| `signals` | `idx_signals_user_gen` | `(user_id, generated_at DESC)` | B-Tree | 사용자별 최신 |
| `signals` | `idx_signals_active` | `(user_id, generated_at DESC)` | B-Tree Partial `WHERE status = 'ACTIVE'` | 활성 시그널 |
| `signals` | `idx_signals_stock_date` | `(stock_id, generated_at DESC)` | B-Tree | 종목별 |
| `signals` | `uq_signals_public_id` | `public_id` | B-Tree UNIQUE | 외부 조회 |
| `ml_predictions` | `idx_ml_pred_stock_base` | `(stock_id, base_date DESC, horizon)` | B-Tree | 최신 예측 조회 |

### 2.4 매매 도메인 (`tp_trade`)

| 테이블 | 인덱스 | 컬럼 | 종류 | 목적 |
|---|---|---|---|---|
| `strategies` | `idx_strategies_user_active` | `(user_id, active)` | B-Tree | 사용자 활성 전략 |
| `strategies` | `uq_strategies_public_id` | `public_id` | B-Tree UNIQUE | - |
| `strategies` | `idx_strategies_user_deleted` | `user_id` | B-Tree Partial `WHERE deleted_at IS NULL` | 살아있는 전략 |
| `orders` | `idx_orders_user_ordered` | `(user_id, ordered_at DESC)` | B-Tree (파티션별) | 사용자별 주문 이력 |
| `orders` | `idx_orders_status_mode` | `(status, trade_mode)` | B-Tree Partial `WHERE status IN ('NEW','PARTIAL','PENDING')` | 미체결 |
| `orders` | `idx_orders_strategy` | `strategy_id` | B-Tree | 전략 성과 집계 |
| `orders` | `uq_orders_idempotency` | `(user_id, idempotency_key)` | B-Tree UNIQUE | 멱등성 |
| `orders` | `uq_orders_public_id` | `public_id` | B-Tree UNIQUE | - |
| `orders` | `idx_orders_ordered_brin` | `ordered_at` | BRIN | 월별 스캔 |
| `fills` | `idx_fills_order` | `order_id` | B-Tree | 주문→체결 |
| `fills` | `idx_fills_user_filled` | `(user_id, filled_at DESC)` | B-Tree | 사용자 체결 이력 |
| `fills` | `idx_fills_stock_filled` | `(stock_id, filled_at DESC)` | B-Tree | 종목별 |
| `positions` | `uq_positions_user_stock_mode` | `(user_id, stock_id, trade_mode)` | B-Tree UNIQUE | 단일 포지션 |
| `positions` | `idx_positions_user_mode` | `(user_id, trade_mode)` | B-Tree | 보유 리스트 |
| `portfolios` | `idx_portfolios_user_snap` | `(user_id, snapshot_at DESC)` | B-Tree | 자산 추이 |
| `daily_pnl` | (PK) | `(user_id, trade_date, trade_mode)` | B-Tree | 일별 손익 |
| `trade_limits` | (PK) | `user_id` | B-Tree | 1:1 |
| `kill_switch_log` | `idx_kill_user_ts` | `(user_id, triggered_at DESC)` | B-Tree | 이력 |
| `backtest_runs` | `idx_bt_runs_user_status` | `(user_id, status, created_at DESC)` | B-Tree | 잡 상태 |
| `backtest_runs` | `uq_bt_runs_job_id` | `job_id` | B-Tree UNIQUE | - |
| `backtest_trades` | `idx_bt_trades_run` | `run_id` | B-Tree | run 종속 |

### 2.5 알림 도메인 (`tp_notify`)

| 테이블 | 인덱스 | 컬럼 | 종류 | 목적 |
|---|---|---|---|---|
| `notifications` | `idx_noti_user_created` | `(user_id, created_at DESC)` | B-Tree | 사용자별 |
| `notifications` | `idx_noti_unread` | `(user_id, created_at DESC)` | B-Tree Partial `WHERE read = false` | 읽지 않은 |
| `alert_rules` | `idx_alert_user_event` | `(user_id, event_type)` | B-Tree | 매칭 |

### 2.6 감사 도메인 (`tp_audit`)

| 테이블 | 인덱스 | 컬럼 | 종류 | 목적 |
|---|---|---|---|---|
| `audit_trade_mode` | `idx_atm_user_ts` | `(user_id, created_at DESC)` | B-Tree | 사용자별 |
| `audit_order_history` | `idx_aoh_order` | `order_id` | B-Tree | 주문 추적 |
| `audit_order_history` | `idx_aoh_created` | `created_at` | BRIN | 기간 스캔 |
| `audit_risk_event` | `idx_are_user_ts` | `(user_id, created_at DESC)` | B-Tree | 사용자별 |
| `audit_role_change` | `idx_arc_user_ts` | `(user_id, created_at DESC)` | B-Tree | - |

---

## 3. 파티셔닝 전략

### 3.1 파티셔닝 대상 테이블

| 테이블 | 방식 | 파티션 단위 | 보관 정책 | 사유 |
|---|---|---|---|---|
| `tp_market.price_minute` | RANGE | **월별** (`ts`) | 분봉 12개월, 5분/15분/30분 60개월 | 시세 누적 (예: 2500종목 × 390분 × 250일 = 2.4억행/년) |
| `tp_trade.orders` | RANGE | **월별** (`ordered_at`) | 10년 | 법정 보존 + 일일 조회 격리 |
| `tp_trade.fills` | RANGE | **월별** (`filled_at`) | 10년 | 동상 |
| `tp_audit.audit_order_history` | RANGE | **월별** (`created_at`) | 10년 | append-only, 대량 |
| `tp_notify.notifications` | RANGE | **월별** (`created_at`) | 6개월 | 알림 단기성 |
| `tp_market.price_daily` | 미파티셔닝 | - | 5년 | 일봉은 누적 < 5천만행, 단일 테이블로 충분 |
| `tp_analysis.indicators_daily` | 미파티셔닝 | - | 5년 | 동상 |

### 3.2 파티션 키 선정 기준

- **시간 컬럼이 항상 WHERE 절에 포함되는가?** → YES → RANGE 파티셔닝
- **WHERE에 user_id가 항상 포함되는가?** → 일부 YES → 파티션 키는 시간, 서브 인덱스 (user_id, ts)
- **HASH 파티셔닝?** → 사용자 분포가 균등하지 않아 채택하지 않음

### 3.3 파티션 자동 관리

- **신규 파티션 생성**: 매월 25일 02:00 cron으로 다음 달 파티션 사전 생성 (스크립트: `scripts/db/create_partition.sh`)
- **오래된 파티션 분리**: 보관 기간 초과 파티션은 `DETACH PARTITION` 후 콜드 스토리지(S3/Parquet)로 export → `DROP TABLE`
- **파티션 명명**: `<parent>_yYYYYmMM` (예: `price_minute_y2026m05`)
- **기본 파티션(DEFAULT)**: 운영 안전망용 `<parent>_default` 1개 항상 유지 (모니터링하여 0행 유지)

### 3.4 파티션 인덱스 정책

- 부모 테이블에 인덱스를 선언하면 PostgreSQL 11+에서 자식 파티션에 자동 전파.
- UNIQUE 제약은 파티션 키를 포함해야 함 → `UNIQUE (stock_id, ts)` 가능 (PK 자체에 ts 포함).
- 멱등성 키처럼 파티션 키 미포함 UNIQUE는 **파티션별 인덱스 + 애플리케이션 가드**로 보완.

---

## 4. 통계 및 Vacuum 전략

### 4.1 Autovacuum 튜닝 (테이블별)

| 테이블 분류 | 패턴 | autovacuum 설정 |
|---|---|---|
| 마스터(stocks, sectors) | 거의 변경 없음 | 기본값 |
| 사용자 데이터(users, settings) | 중간 빈도 | 기본값 |
| 시그널/추천 | 매일 적재 + 일부 갱신 | `autovacuum_vacuum_scale_factor=0.05` |
| 주문/체결 | 고빈도 INSERT, 일부 UPDATE | `autovacuum_vacuum_scale_factor=0.02`, `autovacuum_analyze_scale_factor=0.02` |
| 시세 분봉(`price_minute`) | 대량 INSERT-only | `autovacuum_enabled=true`, `autovacuum_vacuum_insert_scale_factor=0.05` (PG13+) |
| 알림(`notifications`) | 빈번한 read/update(read=true) | `autovacuum_vacuum_scale_factor=0.05` |
| 감사 로그 | append-only | 기본값 |

### 4.2 통계 갱신 (`ANALYZE`)

- 시세 적재 직후 `ANALYZE` 수동 실행 (cron):
  ```
  ANALYZE tp_market.price_minute;
  ANALYZE tp_market.price_daily;
  ANALYZE tp_analysis.indicators_daily;
  ```
- `default_statistics_target = 100` (기본), 시세 테이블만 `ALTER TABLE ... ALTER COLUMN ts SET STATISTICS 500`.

### 4.3 부풀림(Bloat) 모니터링

- `pg_stat_user_tables`, `pgstattuple` 확장으로 주기 점검(주 1회).
- `n_dead_tup / n_live_tup > 20%` 테이블은 수동 `VACUUM FULL` 또는 `pg_repack` 적용 (off-peak).

---

## 5. 쿼리 패턴 매핑

자주 발생하는 쿼리와 대응 인덱스:

| 쿼리 | 사용 인덱스 |
|---|---|
| 대시보드 보유 종목 (사용자별 positions) | `idx_positions_user_mode` |
| 대시보드 일일 손익 | `daily_pnl` PK |
| 추천주 TOP5 | `idx_reco_date_score` |
| 시그널 활성 카운트 | `idx_signals_active` |
| 사용자 주문 이력 (월 단위) | 파티션 프루닝 + `idx_orders_user_ordered` |
| 종목 일봉 차트 (1년) | `price_daily` PK |
| 종목 5분봉 (1개월) | `price_minute` 파티션 프루닝 + PK |
| 종목 검색 (자동완성) | `idx_stocks_name_trgm` (pg_trgm) |
| 섹터별 등락률 랭킹 | `sector_metrics_daily` PK |
| 골든크로스 스캐너 | `idx_ind_daily_macd_golden` (부분 인덱스) |
| 사용자 알림 미읽음 카운트 | `idx_noti_unread` (부분 인덱스) |

---

## 6. 인덱스 미사용/중복 점검 절차

월 1회 수행:

```sql
-- 사용되지 않는 인덱스
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE 'uq_%'
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;

-- 중복 인덱스 후보
SELECT a.indexrelid::regclass, b.indexrelid::regclass
FROM pg_index a JOIN pg_index b ON a.indrelid = b.indrelid
WHERE a.indexrelid < b.indexrelid
  AND a.indkey::text = b.indkey::text;
```

---

## 7. 슬로우 쿼리 모니터링

- `pg_stat_statements` 확장 활성화.
- `track_activity_query_size = 4096`, `pg_stat_statements.max = 5000`.
- 일 1회 슬로우 쿼리 TOP-50 리포트 → 환경 변수 `LOG_MIN_DURATION_STATEMENT = 500ms`.
- pgBadger로 주간 리포트 생성, BackendSenior에 공유.

---

## 8. 연결 풀 및 락 모니터링

| 항목 | 값 |
|---|---|
| `max_connections` | 200 |
| 권장 풀러 | PgBouncer (transaction mode), 풀 100 |
| 락 대기 알람 | `pg_stat_activity.wait_event_type='Lock'` 5초 초과 시 알림 |
| 데드락 로깅 | `log_lock_waits = on`, `deadlock_timeout = 1s` |

---

## 9. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DBA | 최초 작성 |
