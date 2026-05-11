# Phase 1-C 인덱스 운영 가이드

| 항목 | 내용 |
|---|---|
| 문서명 | Phase 1-C 인덱스 운영 가이드 |
| 문서 ID | DBA-IDX-1C |
| 버전 | v0.1 |
| 작성일 | 2026-05-11 |
| 작성자 | DBA Agent |
| 검토자 | DevLead, BackendSenior |
| 대상 | tenant-service / member-service / code-policy-service |

---

## 1. 목적

Phase 1-C(테넌트/회원/코드/정책) 마이그레이션 V1에서 생성되는 **인덱스의 의도와 검증 쿼리**를 정리한다. BackendSenior가 쿼리를 작성하기 전에 본 문서의 EXPLAIN ANALYZE 패턴을 확인하여 인덱스 적합성을 점검한다.

운영 환경에서 신규 인덱스 추가가 필요한 경우 **반드시 EXPLAIN ANALYZE → 실제 부하 측정 → DevLead 합의** 후 적용한다(DBA 행동 원칙).

---

## 2. 테이블별 인덱스 매트릭스

### 2.1 tenant-service

| 인덱스 | 컬럼 | 종류 | 용도 |
|---|---|---|---|
| `pk_tnt_tenant` | `id` | B-Tree(PK) | 기본키 |
| `uk_tnt_tenant_public_id` | `public_id` | UNIQUE | 외부 ULID 조회 |
| `uk_tnt_tenant_code_active` | `LOWER(code)` partial(`deleted_at IS NULL`) | UNIQUE Functional | 코드 중복 차단(대소문자 무시) |
| `ix_tnt_tenant_status` | `status` partial | B-Tree | 활성 테넌트 목록 |
| `uk_tnt_library_tenant_code` | `(tenant_id, LOWER(code))` partial | UNIQUE Functional | 테넌트 내 라이브러리 코드 |
| `ix_tnt_library_tenant_status` | `(tenant_id, status)` partial | 복합 | 활성 라이브러리 목록 |
| `uk_tnt_library_branch_lib_code` | `(library_id, LOWER(code))` partial | UNIQUE Functional | 라이브러리 내 분관 코드 |
| `ix_tnt_library_branch_tenant_lib` | `(tenant_id, library_id, status)` partial | 복합 | 분관 목록 화면 |
| `uk_tnt_tenant_setting_key` | `(tenant_id, key)` | UNIQUE | 설정 키 조회 |
| `ix_tnt_outbox_status_occurred` | `(status, occurred_at)` partial | 복합 | Outbox 폴링 |

### 2.2 member-service

| 인덱스 | 컬럼 | 종류 | 용도 |
|---|---|---|---|
| `uk_mbr_member_tenant_member_no` | `(tenant_id, member_no)` partial | UNIQUE | 회원번호 유일성 |
| `ix_mbr_member_tenant_status` | `(tenant_id, status)` partial | 복합 | 활성 회원 목록 |
| `ix_mbr_member_tenant_library` | `(tenant_id, library_id)` | 복합 | 라이브러리별 회원 |
| `ix_mbr_member_iam_user` | `iam_user_id` partial | B-Tree | IAM 연동 매핑 |
| `gx_mbr_member_name_trgm` | `name_normalized gin_trgm_ops` | GIN(trgm) | 이름 부분일치 검색 |
| `gx_mbr_member_email_trgm` | `email_lower gin_trgm_ops` | GIN(trgm) | 이메일 부분일치 |
| `gx_mbr_member_phone_trgm` | `phone_normalized gin_trgm_ops` | GIN(trgm) | 전화 부분일치 |
| `uk_mbr_member_card_tenant_no` | `(tenant_id, card_no)` partial | UNIQUE | 회원증 번호 |
| `uk_mbr_member_card_tenant_barcode` | `(tenant_id, barcode)` partial | UNIQUE | 회원증 바코드 |
| `uk_mbr_member_card_tenant_rfid` | `(tenant_id, rfid_uid)` partial | UNIQUE | RFID UID |
| `uk_mbr_member_address_default` | `(member_id)` partial(`is_default=TRUE`) | UNIQUE | 기본 주소 1건 보장 |
| `ix_mbr_member_consent_member` | `(member_id, kind, agreed_at DESC)` | 복합 | 최신 동의 조회 |
| `uk_mbr_member_role_active` | `(member_id, role_code)` partial(`revoked_at IS NULL`) | UNIQUE | 활성 역할 1건 |
| `ix_mbr_outbox_status_occurred` | `(status, occurred_at)` partial | 복합 | Outbox 폴링 |

### 2.3 code-policy-service

| 인덱스 | 컬럼 | 종류 | 용도 |
|---|---|---|---|
| `uk_cd_code_group_global_code` | `group_code` partial(`tenant_id IS NULL`) | UNIQUE | 글로벌 그룹코드 유일 |
| `uk_cd_code_group_tenant_code` | `(tenant_id, group_code)` partial | UNIQUE | 테넌트 그룹코드 유일 |
| `uk_cd_code_group_code` | `(group_id, code)` partial | UNIQUE | 그룹 내 코드 유일 |
| `ix_cd_code_group` | `(group_id, sort_order)` | 복합 | 코드 목록 정렬 조회 |
| `ix_cd_code_parent` | `parent_id` | B-Tree | 트리 구조 자식 조회 |
| `gx_cd_code_attrs` | `attrs_json` | GIN | JSONB 키 검색 |
| `ix_pol_policy_scope_eff` | `(scope, effective_from, effective_to)` | 복합 | 유효 정책 조회 |
| `gx_pol_policy_config` | `config_json` | GIN | 정책 룰 키 검색 |
| `ix_pol_policy_assignment_target` | `(target_type, target_id, priority)` | 복합 | 대상별 정책 우선순위 |

---

## 3. EXPLAIN ANALYZE 검증 쿼리 (핵심 5종)

다음 쿼리는 **운영 배포 전 회귀 검증 시 반드시 측정**한다. 모든 쿼리는 `SET app.current_tenant = '1'` 컨텍스트로 실행한다.

### 3.1 회원 부분일치 검색 (이름)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, member_no, name, status
  FROM mbr_member
 WHERE name_normalized LIKE '%kim%'
 ORDER BY member_no
 LIMIT 50;
```

- 기대 계획: `Bitmap Index Scan on gx_mbr_member_name_trgm` → `Bitmap Heap Scan`
- 임계: 50만 건 기준 50ms 이내. 초과 시 Material Path 또는 `tsvector` 인덱스 검토.

### 3.2 라이브러리별 활성 회원 페이징

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, member_no, name
  FROM mbr_member
 WHERE library_id = 1
   AND status = 'ACTIVE'
   AND deleted_at IS NULL
 ORDER BY id DESC
 LIMIT 100 OFFSET 0;
```

- 기대 계획: `Index Scan on ix_mbr_member_tenant_library` (또는 `ix_mbr_member_tenant_status`)
- 임계: 50만 건 기준 10ms 이내.

### 3.3 코드 조회 (테넌트 우선, 글로벌 fallback)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.code, c.name, c.attrs_json, g.tenant_id
  FROM cd_code c
  JOIN cd_code_group g ON g.id = c.group_id
 WHERE g.group_code = 'MEMBER_TYPE'
   AND (g.tenant_id IS NULL OR g.tenant_id = 1)
   AND c.enabled_yn = TRUE
   AND c.deleted_at IS NULL
 ORDER BY g.tenant_id DESC NULLS LAST, c.sort_order;
```

- 기대 계획: `Index Scan on uk_cd_code_group_global_code` + `uk_cd_code_group_tenant_code` → Join → `Index Scan on ix_cd_code_group`
- 임계: 코드 1만 건 기준 5ms 이내. 캐시(Redis) 사용이 권장.

### 3.4 Outbox 폴링 쿼리

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, aggregate_type, aggregate_id, event_type, payload, tenant_id
  FROM mbr_outbox
 WHERE status = 'PENDING'
 ORDER BY occurred_at
 FOR UPDATE SKIP LOCKED
 LIMIT 100;
```

- 기대 계획: `Index Scan on ix_mbr_outbox_status_occurred`
- 임계: PENDING 1만 건 기준 20ms 이내. `FOR UPDATE SKIP LOCKED` 가 핵심 — 멀티 워커 분산.

### 3.5 회원증 RFID 조회 (출입/대출 핵심)

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT m.id, m.member_no, m.name, m.status
  FROM mbr_member_card c
  JOIN mbr_member      m ON m.id = c.member_id
 WHERE c.rfid_uid = '0123ABCD'
   AND c.status   = 'ACTIVE'
   AND c.deleted_at IS NULL;
```

- 기대 계획: `Index Scan on uk_mbr_member_card_tenant_rfid` → Nested Loop → `Index Scan on pk_mbr_member`
- 임계: 5ms 이내. 출입 게이트의 SIP2 통신 SLA(150ms) 확보 필수.

---

## 4. 인덱스 추가/변경 절차

1. 후보 쿼리의 **현재 EXPLAIN ANALYZE 결과** 첨부.
2. 신규 인덱스의 `CREATE INDEX CONCURRENTLY` 스크립트 작성.
3. 스테이징에 적용 → **before/after EXPLAIN 비교**.
4. DevLead 합의 → 신규 Flyway 마이그레이션(`Vx__`) PR 등록.
5. 운영 적용은 트래픽 낮은 시간 + `CONCURRENTLY` 옵션 + `lock_timeout = '30s'`.

---

## 5. 모니터링 권장 쿼리

- 사용 안 되는 인덱스 식별: `pg_stat_user_indexes WHERE idx_scan = 0` (운영 7일 이상 관찰).
- 비대해진 인덱스: `pgstattuple` 또는 `pg_relation_size` 비교.
- Bloat: 야간 `REINDEX CONCURRENTLY` 정책(GIN trgm 인덱스가 특히 비대 우려).

---

## 6. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v0.1 | 2026-05-11 | DBA Agent | Phase 1-C 초안 — tenant/member/code-policy 인덱스 매트릭스 + EXPLAIN 검증 쿼리 5종 |
