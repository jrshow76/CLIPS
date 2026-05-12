# TradePilot 스키마 개요 및 테이블 카탈로그

> 문서 ID: 31_SCHEMA_OVERVIEW
> 버전: v1.0
> 작성자: DBA
> 최종 수정일: 2026-05-12

본 문서는 TradePilot PostgreSQL 데이터베이스의 스키마 구조, 도메인별 책임, 테이블 카탈로그를 정의한다.

---

## 1. 데이터베이스 설정 표준

| 항목 | 값 | 근거 |
|---|---|---|
| PostgreSQL 버전 | 15.x | LTS, 파티셔닝/JIT/btree 개선 |
| Encoding | UTF8 | 다국어 처리 |
| Collation / Ctype | `ko_KR.UTF-8` 또는 `C.UTF-8` | 한글 정렬 + 인덱스 효율 |
| Timezone | `Asia/Seoul` | KST 표준 |
| Default tablespace | `pg_default` | 기본 |
| Default schema search_path | `tp_user, tp_market, tp_analysis, tp_trade, tp_notify, tp_audit, public` | 도메인 격리 |
| 통화/금액 | `NUMERIC(20, 4)` | 원화 + 소수점 4자리 |
| 시세/지표 | `NUMERIC(20, 8)` | 백분율/비율 정밀도 |
| 시간 | `TIMESTAMPTZ` | UTC 저장, KST 표현 |
| 텍스트 ID | `UUID` (pgcrypto `gen_random_uuid()`) | 외부 노출 |
| 내부 PK | `BIGSERIAL` | 인덱스 효율 |

---

## 2. 스키마 구조

| 스키마 | 책임 | 주요 테이블 수 | 권한 |
|---|---|---:|---|
| `tp_user` | 사용자/인증/세션 | 7 | app_user: RW |
| `tp_market` | 종목/시세/섹터 마스터 | 8 | app_user: R, operator: RW |
| `tp_analysis` | 지표 캐시/추천/시그널/ML 예측 | 5 | app_user: R, worker: RW |
| `tp_trade` | 전략/주문/체결/포지션/한도/Kill Switch/백테스트 | 12 | app_user: RW |
| `tp_notify` | 알림 큐/채널/룰 | 3 | app_user: RW |
| `tp_audit` | 감사 로그(append-only) | 4 | app_user: APPEND, admin: R |

> 도메인별 스키마 분리는 권한·백업·파티션 격리를 가능하게 한다. 운영자(operator)는 마스터 데이터 갱신만 가능하며 거래 데이터에는 접근하지 못한다.

---

## 3. 테이블 카탈로그 (총 39개)

### 3.1 사용자 도메인 `tp_user` (7개)

| # | 테이블 | 목적 | 보관 정책 | 비고 |
|---|---|---|---|---|
| 1 | `users` | 사용자 기본 정보, 인증 | 영구(탈퇴 후 30일→익명화) | 핵심 |
| 2 | `user_profiles` | 프로필 부가정보(아바타/타임존) | 사용자 종속 | 1:1 |
| 3 | `user_settings` | 알림/스케줄/테마 | 사용자 종속 | 1:1, JSONB |
| 4 | `otp_codes` | OTP 코드 이력 | 7일 후 삭제 | 단방향 해시 |
| 5 | `sessions` | Refresh token 세션 | 만료 후 30일 | 토큰 회전 추적 |
| 6 | `user_favorites` | 종목 즐겨찾기 | 사용자 종속 | M:N |
| 7 | `audit_login` | 로그인/로그아웃 이력 | 1년 | 보안 추적 |

### 3.2 시장 도메인 `tp_market` (8개)

| # | 테이블 | 목적 | 보관 정책 | 비고 |
|---|---|---|---|---|
| 8 | `stocks` | 종목 마스터 | 영구 | 마스터 데이터 |
| 9 | `sectors` | 섹터/업종 마스터 | 영구 | 마스터 데이터 |
| 10 | `stock_sectors` | 종목-섹터 매핑 | 영구 | M:N |
| 11 | `corporate_actions` | 무상증자/유상증자/액면분할/배당 | 영구 | adj_close 산출 |
| 12 | `price_daily` | 일봉 | 5년 (NFR-DATA-001) | (stock_id, trade_date) UNIQUE |
| 13 | `price_minute` | 분봉 (1/5/15/30분) | 1년(원시), 5년(5분 이상 집계) | 월별 RANGE 파티셔닝 |
| 14 | `market_index` | 시장 지수 마스터(KOSPI/KOSDAQ) | 영구 | 마스터 |
| 15 | `market_index_daily` | 지수 일봉 | 5년 | - |

### 3.3 분석 도메인 `tp_analysis` (5개)

| # | 테이블 | 목적 | 보관 정책 | 비고 |
|---|---|---|---|---|
| 16 | `indicators_daily` | 일봉 기준 지표 캐시 | 5년 | 와이드 컬럼(MA/RSI/MACD/BB/OBV/VWAP/Stoch/ATR) |
| 17 | `sector_metrics_daily` | 섹터 일별 등락/자금흐름/상관 | 5년 | 히트맵 캐시 |
| 18 | `recommendations` | 일별 추천 종목 | 1년 | 전략 × 종목 × 일자 |
| 19 | `signals` | 사용자별 매매 시그널 | 2년(상태별) | status 컬럼 인덱스 |
| 20 | `ml_predictions` | LSTM 예측 결과 | 1년 | 모델 버전 컬럼 |

### 3.4 매매 도메인 `tp_trade` (12개)

| # | 테이블 | 목적 | 보관 정책 | 비고 |
|---|---|---|---|---|
| 21 | `strategies` | 사용자 전략 정의 | 영구(소프트 삭제) | JSONB 룰 |
| 22 | `strategy_rules` | 룰 행 분해(검색/통계용) | 전략 종속 | 옵션 |
| 23 | `orders` | 주문 헤더 | 10년 (NFR-DATA-002) | 월별 RANGE 파티셔닝 |
| 24 | `fills` | 체결 | 10년 | 월별 RANGE 파티셔닝 |
| 25 | `positions` | 현재 보유 포지션 | 영구 | 모드별(trade_mode) 분리 |
| 26 | `portfolios` | 일별 자산 스냅샷 | 10년 | 리포트 가속 |
| 27 | `daily_pnl` | 일별 손익 집계 | 10년 | - |
| 28 | `trade_limits` | 사용자 한도 설정 | 영구 | 1:1 |
| 29 | `kill_switch_log` | 비상정지 이력 | 영구 | 감사 |
| 30 | `backtest_runs` | 백테스트 잡 | 1년 | 큐 잡 관리 |
| 31 | `backtest_results` | 저장된 결과 | 1년 | label 별 |
| 32 | `backtest_trades` | 백테스트 거래 내역 | 1년 | run_id 파티션 가능 |

### 3.5 알림 도메인 `tp_notify` (3개)

| # | 테이블 | 목적 | 보관 정책 | 비고 |
|---|---|---|---|---|
| 33 | `notifications` | 인앱/외부 알림 큐 | 90일 | 읽음 처리 후 30일 |
| 34 | `notification_channels` | 사용자 채널 설정 | 영구 | 1:1 |
| 35 | `alert_rules` | 사용자 알림 룰 | 영구 | - |

### 3.6 감사 도메인 `tp_audit` (4개)

| # | 테이블 | 목적 | 보관 정책 | 비고 |
|---|---|---|---|---|
| 36 | `audit_trade_mode` | SIM↔LIVE 전환 이력 | 10년 | append-only |
| 37 | `audit_order_history` | 주문 상태 변경 이력 | 10년 | 월별 파티셔닝 |
| 38 | `audit_role_change` | 권한 변경 이력 | 10년 | append-only |
| 39 | `audit_risk_event` | 리스크 이벤트(한도초과/강제청산/슬리피지) | 10년 | append-only |

---

## 4. 명명 규칙 (Naming Convention)

| 객체 | 규칙 | 예시 |
|---|---|---|
| 테이블 | `snake_case`, 복수형 | `users`, `orders`, `price_daily` |
| 컬럼 | `snake_case` | `user_id`, `trade_mode`, `created_at` |
| PK | `id` | `users.id` |
| FK | `<참조테이블단수>_id` | `user_id`, `stock_id` |
| 외부 노출 ID | `public_id` (UUID) | `signals.public_id` |
| 인덱스 | `idx_<table>_<columns>` | `idx_orders_user_id_ordered_at` |
| 유니크 인덱스 | `uq_<table>_<columns>` | `uq_users_email` |
| 외래키 제약 | `fk_<table>_<column>` | `fk_orders_user_id` |
| 체크 제약 | `ck_<table>_<col>` | `ck_users_role` |
| 파티션 자식 | `<parent>_yYYYYmMM` | `price_minute_y2026m05` |
| 트리거 | `trg_<table>_<event>` | `trg_users_updated_at` |
| 시퀀스 | `seq_<table>_<column>` | 자동 (BIGSERIAL) |

---

## 5. 공통 컬럼 규약

모든 비즈니스 테이블은 다음 표준 컬럼을 포함한다:

| 컬럼 | 타입 | 기본값 | 비고 |
|---|---|---|---|
| `id` | `BIGSERIAL` | - | PK |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `now()` | 생성 시각 |
| `updated_at` | `TIMESTAMPTZ NOT NULL` | `now()` | 트리거로 갱신 |
| `deleted_at` | `TIMESTAMPTZ NULL` | NULL | 소프트 삭제 대상 테이블만 |

> 시계열 테이블(`price_daily`, `price_minute`, `indicators_daily`)은 `updated_at`을 생략하고 `created_at`만 유지하여 쓰기 비용을 절감한다.

---

## 6. 데이터 타입 표준

| 의미 | 권장 타입 | 비고 |
|---|---|---|
| 통화 (KRW) | `NUMERIC(20, 4)` | 원화 + 정밀도 |
| 수량 (주) | `NUMERIC(20, 4)` | 분할 거래 대비 |
| 비율 (%) | `NUMERIC(10, 4)` | -999.9999~999.9999 |
| 시세 가격 | `NUMERIC(20, 4)` | - |
| 거래대금 | `NUMERIC(20, 4)` | 대형주 대비 |
| 거래량 | `BIGINT` | 주식 수량 |
| 이메일 | `CITEXT` | 대소문자 무시 |
| URL | `TEXT` | 길이 제한 없음 |
| IP | `INET` | IPv4/IPv6 |
| JSON 페이로드 | `JSONB` | 인덱스 가능 |
| 종목코드 | `VARCHAR(6)` | KRX 6자리 |
| 상태/Enum | `VARCHAR(20)` + CHECK | enum 타입 회피(스키마 변경 비용) |

> Enum 타입을 사용하지 않고 `VARCHAR + CHECK` 패턴을 사용하는 이유: 값 추가 시 `ALTER TYPE`이 락을 잡고, 마이그레이션 도구(Alembic) 친화성이 낮기 때문이다.

---

## 7. 외래키 ON DELETE 정책

| 관계 | 정책 | 사유 |
|---|---|---|
| `users` → `orders/fills` | SET NULL + 익명화 | 법정 10년 보존, 사용자 식별만 제거 |
| `users` → `user_settings/user_profiles` | CASCADE | 사용자 종속 데이터 |
| `users` → `sessions/otp_codes` | CASCADE | 보안 데이터 정리 |
| `stocks` → `price_*` | CASCADE | 상장폐지 시 시세 정리(또는 보존 정책에 따라 RESTRICT) |
| `strategies` → `orders` | SET NULL | 전략 삭제 후에도 주문 이력 유지 |
| `orders` → `fills` | CASCADE | 파생 데이터 |
| `users` → `audit_*` | RESTRICT | 감사 데이터 무결성 |

---

## 8. 트랜잭션 격리 수준

| 시나리오 | 격리 수준 | 비고 |
|---|---|---|
| 일반 조회 | `READ COMMITTED` (기본) | PostgreSQL 기본 |
| 주문 생성 (Risk Guard) | `REPEATABLE READ` | 한도 검사 일관성 |
| 강제 청산 / Kill Switch | `SERIALIZABLE` | 동시성 차단 |
| 시세/지표 배치 적재 | `READ COMMITTED` + `COPY` | 처리량 우선 |
| 백테스트 결과 저장 | `READ COMMITTED` | 단일 잡 |

---

## 9. 핵심 비즈니스 제약

| 제약 | 구현 |
|---|---|
| 이메일 유일성 | `users.email` UNIQUE + CITEXT |
| 사용자당 활성 전략 ≤ N | 애플리케이션 검증 + 통계 인덱스 |
| 주문 멱등성 | `orders.idempotency_key` UNIQUE (24h 윈도우) |
| 주문 모드 일치 | CHECK + 애플리케이션 가드(X-Trade-Mode) |
| 일별 종목 일봉 유일 | `price_daily(stock_id, trade_date)` UNIQUE |
| 분봉 (stock, ts, interval) 유일 | 파티션별 UNIQUE 인덱스 |
| 한도 음수 금지 | CHECK `daily_buy_amount >= 0` |

---

## 10. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DBA | 최초 작성 |
