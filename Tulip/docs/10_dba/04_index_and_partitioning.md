# 인덱스 & 파티셔닝 전략 (Index & Partitioning Strategy)

| 항목 | 내용 |
|---|---|
| 문서명 | 인덱스 & 파티셔닝 전략 |
| 문서 ID | DBA-04 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DBA Agent |
| 검토자 | DevLead, BackendSenior |
| 상태 | 초안 |
| 대상 DBMS | PostgreSQL 15+ |

---

## 1. 문서 개요

본 문서는 Planner 6개 도메인 핵심 쿼리 패턴을 분석하여 인덱스·파티셔닝 전략을 정의한다. 비기능 요구사항(API P99 ≤ 500ms·대출 단건 ≤ 500ms·검색 ≤ 5초)을 만족해야 한다.

### 1.1 인덱스 명명 규약 (재인용)

| 접두사 | 종류 |
|---|---|
| `ix_` | 일반 B-Tree |
| `uk_` | UNIQUE |
| `gx_` | GIN |
| `bx_` | BRIN |
| `fx_` | Functional / Expression |
| `tx_` | trigram (`pg_trgm`) (GIN/GiST 위에 의미적 표기) |
| `ex_` | Exclusion 제약 (시간 중첩 등) |

### 1.2 인덱스 설계 원칙

1. **읽기 패턴이 분명한 컬럼만** 인덱싱 — 쓰기 성능 저하 균형.
2. **부분 인덱스(WHERE 절)** 적극 활용 — 활성 대출, 미해결 연체료 등 좁은 분포.
3. **표현식 인덱스** — JSONB 서브필드, lower(), date_trunc().
4. **복합 인덱스의 컬럼 순서**: 카디널리티 + 선택도 + WHERE 빈도 기준. `(tenant_id, library_id, ...)` 패턴 표준.
5. **BRIN** — 시계열 대용량(출입이력·감사로그·대출이력)에 우선.
6. **모든 인덱스는 RLS 호환** — `tenant_id` 선두.

---

## 2. 도메인별 핵심 쿼리 패턴 분석

### 2.1 CMN (회원)

| 쿼리 패턴 | 빈도 | 인덱스 |
|---|---|---|
| 회원증·바코드로 회원 조회 | 매우 높음 | `uk_member_no(tenant_id, member_no)` |
| 이메일·전화로 회원 검색 | 높음 | `ix_member_email_hash`, `ix_member_phone_hash` |
| 회원명 부분일치(name LIKE %) | 중 | `ix_member_name_trgm` (pg_trgm GIN) |
| 상태별 회원 통계 | 낮음 | `ix_member_status` |
| SSO subject 매핑 | 매우 높음 (로그인) | `uk_member_sso(tenant_id, sso_provider, sso_subject)` |

### 2.2 CAT (서지)

| 쿼리 패턴 | 빈도 | 인덱스 |
|---|---|---|
| ISBN 정확일치 검색 | 매우 높음 | `ix_bib_isbn(tenant_id, isbn_normalized)` |
| 제목 부분/유사 검색 | 매우 높음 (OPAC) | `gx_bib_title_trgm` + `bib_index_tsv` |
| 저자명 검색 | 높음 | `gx_bib_author_trgm` |
| KDC/DDC 분류 탐색 | 높음 | `ix_bib_kdc`, `ix_bib_ddc` |
| MARC tag별 서브필드 검색 | 중 | `gx_marc_subfields (jsonb_path_ops)`, `fx_marc_245a` |
| 권위레코드 매칭 | 중 | `gx_authority_heading_trgm` |

### 2.3 COL (장서)

| 쿼리 패턴 | 빈도 | 인덱스 |
|---|---|---|
| 등록번호로 자료 조회 | 매우 높음 | `uk_copy_accession` |
| 바코드/RFID로 자료 조회 | 매우 높음 | `uk_copy_barcode`, `uk_copy_rfid` |
| 자료 상태별 필터 | 높음 | `ix_copy_status` (부분 인덱스 `WHERE deleted_at IS NULL`) |
| 서가별 자료 목록 | 중 | `ix_copy_location` |
| 점검 대상 자료 | 낮음 | `ix_copy_class_range` (표현식) |

### 2.4 ACQ (수서)

| 쿼리 패턴 | 빈도 | 인덱스 |
|---|---|---|
| 발주 상태별 목록 | 높음 | `ix_po_status(tenant_id, library_id, status, order_date DESC)` |
| 회원의 희망도서 | 중 | `ix_acqreq_member` |
| 납품처별 발주 | 중 | `ix_po_vendor` |
| 예산 회계연도 잔액 | 높음 | `uk_budget(tenant_id, library_id, fiscal_year, budget_code)` |
| 연속간행물 호 예측 | 중 | `ix_serial_issue_expected_date` |

### 2.5 CIR (열람) — **가장 트래픽 높음**

| 쿼리 패턴 | 빈도 | 인덱스 |
|---|---|---|
| 회원의 활성 대출 조회 | 매우 매우 높음 | `ix_loan_member_status (member_id, status) WHERE status IN ('ACTIVE','OVERDUE')` |
| 자료의 현재 대출 확인 | 매우 매우 높음 | `uk_loan_copy_active (copy_id) WHERE status IN ('ACTIVE','OVERDUE')` |
| 만기 도래 대출 배치 | 일 1회 (대량) | `ix_loan_due (due_date) WHERE status='ACTIVE'` |
| 관별 일자별 대출 | 통계 | `ix_loan_lib_checkout (tenant_id, library_id, checkout_at DESC)` |
| 예약 큐 1순위 | 높음 | `ix_hold_bib_queue (bibliography_id, queue_position) WHERE status='WAITING'` |
| 회원 미납 연체료 | 매우 높음 | `ix_fine_member_pending (member_id, status) WHERE status IN ('PENDING','PARTIAL')` |
| OPAC 검색 로그 통계 | 일배치 | BRIN (`searched_at`) |
| SIP2 트랜잭션 (시계열) | 매우 높음 (장비) | BRIN (`txn_at`) |

### 2.6 ACS (출입) — **시계열 대용량**

| 쿼리 패턴 | 빈도 | 인덱스 |
|---|---|---|
| 게이트 통과 이벤트 적재 | 매우 높음 (write) | RANGE 파티션 + BRIN(`event_at`) |
| 회원 출입이력 | 중 | `ix_ae_member (tenant_id, member_id, event_at DESC)` |
| 게이트 통과 통계 | 일배치 | `ix_ae_gate (library_id, gate_id, event_at DESC)` |
| 재실현황 실시간 | 매우 높음 (read) | Materialized View 또는 Redis 캐시 |
| EAS 경보 조회 | 중 | `ix_eas_lib_time` |

### 2.7 FAC (시설)

| 쿼리 패턴 | 빈도 | 인덱스 |
|---|---|---|
| 좌석 시간대 예약현황 | 매우 높음 (OPAC) | `ix_seat_resv_seat_time (seat_id, reserved_from, reserved_to)` + EXCLUDE 제약 |
| 회원의 예약 | 중 | `ix_seat_resv_member` |
| 회의실 일정 충돌 검사 | 높음 | `ix_room_resv_room_time` |

---

## 3. 핵심 인덱스 카탈로그 (요약)

```sql
-- CMN
CREATE INDEX ix_member_status         ON tlp_cmn_member(tenant_id, status) WHERE deleted_at IS NULL;
CREATE INDEX ix_member_email_hash     ON tlp_cmn_member(tenant_id, email_hash);
CREATE INDEX ix_member_phone_hash     ON tlp_cmn_member(tenant_id, phone_hash);
CREATE INDEX ix_member_name_trgm      ON tlp_cmn_member USING GIN (name_hash gin_trgm_ops);
-- 대출 마감 임박 회원 알림 (조건부)
CREATE INDEX ix_member_active_dueAlert ON tlp_cmn_member(tenant_id)
  WHERE status = 'ACTIVE' AND deleted_at IS NULL;

-- CAT
CREATE INDEX ix_bib_isbn       ON tlp_cat_bibliography(tenant_id, isbn_normalized) WHERE deleted_at IS NULL;
CREATE INDEX ix_bib_kdc        ON tlp_cat_bibliography(tenant_id, classification_kdc);
CREATE INDEX gx_bib_title_trgm ON tlp_cat_bibliography USING GIN (title_main gin_trgm_ops);
CREATE INDEX gx_bib_author_trgm ON tlp_cat_bibliography USING GIN (authors_all gin_trgm_ops);
CREATE INDEX gx_marc_subfields ON tlp_cat_marc_field USING GIN (subfields jsonb_path_ops);

-- COL
CREATE INDEX ix_copy_status    ON tlp_col_copy(tenant_id, library_id, item_status) WHERE deleted_at IS NULL;
CREATE INDEX ix_copy_holding   ON tlp_col_copy(holding_id);
CREATE INDEX ix_copy_location  ON tlp_col_copy(location_id);

-- CIR
CREATE UNIQUE INDEX uk_loan_copy_active ON tlp_cir_loan(copy_id) WHERE status IN ('ACTIVE','OVERDUE');
CREATE INDEX ix_loan_member_status      ON tlp_cir_loan(member_id, status) WHERE status IN ('ACTIVE','OVERDUE');
CREATE INDEX ix_loan_due                ON tlp_cir_loan(due_date) WHERE status = 'ACTIVE';
CREATE INDEX ix_loan_lib_checkout       ON tlp_cir_loan(tenant_id, library_id, checkout_at DESC);
CREATE INDEX ix_hold_bib_queue          ON tlp_cir_hold(bibliography_id, queue_position) WHERE status='WAITING';
CREATE INDEX ix_fine_member_pending     ON tlp_cir_fine(member_id, status) WHERE status IN ('PENDING','PARTIAL');

-- ACS
CREATE INDEX bx_ae_event_at      ON tlp_acs_access_event USING BRIN (event_at);
CREATE INDEX ix_ae_member        ON tlp_acs_access_event(tenant_id, member_id, event_at DESC);

-- FAC
CREATE INDEX ix_seat_resv_seat_time ON tlp_fac_seat_reservation(seat_id, reserved_from, reserved_to);
```

---

## 4. 한글 전문검색(FTS) 전략

OPAC 검색(CIR-060)이 시스템 핵심 UX. 다음 두 단계 전략을 채택한다.

### 4.1 1차: PostgreSQL `pg_trgm` + tsvector

- **장점**: 별도 시스템 없음, 즉시 일관성, RLS 호환.
- **방법**:
  ```sql
  ALTER TABLE tlp_cat_bibliography ADD COLUMN search_tsv tsvector
    GENERATED ALWAYS AS (
      setweight(to_tsvector('simple', coalesce(title_main,'')), 'A') ||
      setweight(to_tsvector('simple', coalesce(authors_all,'')), 'B') ||
      setweight(to_tsvector('simple', coalesce(publisher,'')), 'C') ||
      setweight(to_tsvector('simple', coalesce(title_other,'')), 'D')
    ) STORED;
  CREATE INDEX gx_bib_search_tsv ON tlp_cat_bibliography USING GIN (search_tsv);
  ```
- 한글: `simple` config 사용 + 별도 형태소 분석 미적용(향후 mecab-ko 검토).
- 부분일치(LIKE `%키워드%`)는 `pg_trgm gin_trgm_ops`로 보완.

### 4.2 2차 (Phase 2): 외부 검색엔진(OpenSearch / Elasticsearch)

- 서지 5천만 도달 시 PostgreSQL FTS 한계 도달 → CDC(Debezium) 또는 배치로 색인 동기화.
- DevLead와 협의 — Y2 검토.
- 색인 동기화 큐: `tlp_cat_bib_index_queue` 테이블 + 워커.

---

## 5. 파티셔닝 전략

### 5.1 파티셔닝 후보 테이블

| 테이블 | 적재 추정 | 파티션 키 | 파티션 유형 | 보존 |
|---|---|---|---|---|
| `tlp_acs_access_event` | 1M~10M/월/관 | `event_at` | RANGE 월별 | 5년 (그 후 콜드) |
| `tlp_cmn_audit_log` | 100K~1M/월/테넌트 | `acted_at` | RANGE 월별 | 5년 |
| `tlp_cir_loan` | 1M~10M/년/테넌트 | `checkout_at` | RANGE 연/월별 | 영구(이용내역) |
| `tlp_cir_sip2_transaction` | 10K~1M/일 | `txn_at` | RANGE 월별 | 1년 |
| `tlp_cmn_notification_log` | 100K~1M/월 | `sent_at` | RANGE 월별 | 2년 |
| `tlp_acs_eas_alarm` | 1K~10K/월 | (파티션 없음) | - | 5년 |
| `tlp_acq_budget_transaction` | 10K/년 | `txn_at` | (선택) RANGE 연별 | 영구 |
| `tlp_cir_opac_search_log` | 100K~10M/월 | `searched_at` | RANGE 월별 | 6개월 |

### 5.2 파티션 자동 관리

```sql
-- pg_partman 사용 권고 (PostgreSQL 확장)
CREATE EXTENSION pg_partman;

SELECT partman.create_parent(
  p_parent_table => 'tulip.tlp_acs_access_event',
  p_control      => 'event_at',
  p_type         => 'native',
  p_interval     => 'monthly',
  p_premake      => 6
);

-- 주기 작업: 파티션 자동 생성·옛 파티션 detach
SELECT partman.run_maintenance();
```

- 미사용 시 cron + PL/pgSQL 스크립트로 매월 1일 다음달 파티션 생성.
- 보존기한 경과 파티션은 `DETACH PARTITION` 후 콜드 스토리지(별도 archived 스키마 또는 S3 export) 이전.

### 5.3 파티셔닝 운영 가이드

1. PK는 `(id, 파티션키)` 복합 — PostgreSQL 제약.
2. 글로벌 유니크 제약(예: `accession_no`)이 필요한 테이블은 파티셔닝 비적용.
3. RLS 정책은 부모 테이블에만 정의 → 자식 자동 상속.
4. 파티션 프루닝 활성화: `SET enable_partition_pruning = on;` (기본).
5. 인덱스도 파티션별 — `CREATE INDEX ... ON tlp_acs_access_event ...` 시 모든 자식에 자동 적용 (PostgreSQL 11+).

---

## 6. 통계 · 대시보드 인덱스 전략

### 6.1 Materialized View (집계 캐시)

대시보드(CMN-060) — KPI 표준 통계는 MV로 사전 집계.

```sql
-- 일별·관별 대출 집계
CREATE MATERIALIZED VIEW mv_cir_daily_loan_stat AS
SELECT tenant_id, library_id,
       date_trunc('day', checkout_at)::date AS loan_date,
       COUNT(*) AS loan_count,
       COUNT(DISTINCT member_id) AS unique_members
FROM tlp_cir_loan
WHERE checkout_at >= '2024-01-01'
GROUP BY 1,2,3
WITH NO DATA;

CREATE UNIQUE INDEX uk_mv_cir_daily ON mv_cir_daily_loan_stat(tenant_id, library_id, loan_date);

-- 매일 새벽 갱신 (REFRESH CONCURRENTLY)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_cir_daily_loan_stat;
```

### 6.2 통계용 Read Replica

- Streaming Replication으로 read replica 1대 + 통계 워크로드 분리.
- 무거운 통계 쿼리·KOLIS-NET 통계 양식 생성 등은 read replica로 라우팅.
- 애플리케이션 datasource 분리(BackendSenior 협의).

### 6.3 통계 인덱스 가이드

| 통계 종류 | 인덱스 |
|---|---|
| 분류·자료유형별 장서수 | `ix_copy_class (tenant_id, library_id, item_type, call_no)` 부분 |
| 일자별 대출집계 | MV + `ix_loan_lib_checkout` |
| 인기 자료 Top N | `ix_loan_copy_count` (BRIN) + 주기 집계 MV |
| 회원 활동률 | MV 집계 (월별) |

---

## 7. 인덱스 유지보수

### 7.1 REINDEX 정책

- PostgreSQL 15 `REINDEX CONCURRENTLY` 적극 활용 — 운영 중 다운타임 없이 재구성.
- 분기 1회: GIN 인덱스 점검(`pgstattuple` 모듈로 fragmentation 점검).
- 인덱스 사용량 모니터링: `pg_stat_user_indexes` → 0회 호출 인덱스는 검토 후 제거.

### 7.2 Autovacuum 파라미터 (CIR/ACS 핫 테이블)

```sql
ALTER TABLE tlp_cir_loan SET (
  autovacuum_vacuum_scale_factor = 0.02,
  autovacuum_analyze_scale_factor = 0.01,
  autovacuum_vacuum_cost_limit = 1000
);

ALTER TABLE tlp_acs_access_event SET (
  autovacuum_vacuum_scale_factor = 0.05,
  fillfactor = 90
);
```

### 7.3 HOT update 활용

- 부분 인덱스 활용으로 인덱스 컬럼 변경 빈도 최소화 → HOT update 비율 ↑.

---

## 8. 쿼리 성능 목표·검증

| 쿼리 | P99 목표 | 검증 방법 |
|---|---|---|
| 회원 단건 조회 (member_no) | 5ms | EXPLAIN ANALYZE → Index Scan |
| OPAC 키워드 검색 (1만건 hit, 20건 페이징) | 200ms | GIN scan + LIMIT |
| ISBN 정확매칭 검색 | 10ms | Index Only Scan |
| 대출 처리 트랜잭션 | 500ms | 전체 트랜잭션 시간 |
| 회원 활성 대출 목록 | 30ms | 부분 인덱스 활용 |
| 만기 대출 일배치 (1만건) | 1분 | UPDATE 분할 처리 |
| 출입이력 월간 조회 (1관) | 1초 | 파티션 프루닝 |
| 좌석 예약 충돌 검사 | 50ms | GIST EXCLUDE 또는 인덱스 |

### 8.1 모니터링 도구

- `pg_stat_statements`: 누적 실행시간·호출 횟수 Top 20 매주 점검
- `auto_explain`: 1초 이상 쿼리 자동 EXPLAIN 로깅
- `pgBadger`: 슬로우 로그 리포트
- `Prometheus + pg_exporter`: 지표 수집·Grafana 대시보드

---

## 9. 안티패턴 회피 가이드

| 안티패턴 | 회피책 |
|---|---|
| `SELECT *` | 명시적 컬럼 선택, BackendSenior와 협의 |
| `OR` 조건 다용 | UNION ALL 또는 GIN 인덱스 활용 |
| Function on indexed column (`WHERE LOWER(col)=...`) | 표현식 인덱스 또는 정규화 컬럼 |
| 작은 테이블 큰 인덱스 | 100행 이하 테이블은 인덱스 생성 안 함 |
| `LIKE '%abc%'` 풀스캔 | pg_trgm + GIN |
| 다중 컬럼 정렬 미지원 인덱스 | 정렬 컬럼까지 포함한 복합 인덱스 |
| `IN (수천 건)` 쿼리 | 임시 테이블 + JOIN 또는 VALUES 절 |
| 트랜잭션 내 슬립/외부호출 | 격리수준·락 보유시간 단축 |

---

## 10. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v0.1 | 2026-05-11 | DBA Agent | 도메인별 인덱스·파티셔닝 카탈로그, pg_trgm/BRIN/GIN 적용 전략, MV/Replica 분리 |
