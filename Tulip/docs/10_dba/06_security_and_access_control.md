# DB 보안 & 권한 관리 (Database Security & Access Control)

| 항목 | 내용 |
|---|---|
| 문서명 | DB 보안 & 권한 관리 |
| 문서 ID | DBA-06 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DBA Agent |
| 검토자 | DevLead, PM, BackendSenior |
| 상태 | 초안 |
| 대상 DBMS | PostgreSQL 15+ |

---

## 1. 문서 개요

본 문서는 Tulip+ DB 계층의 **사용자/Role 분리, 권한 매트릭스, RLS 적용, 컬럼 암호화, 마스킹, 감사 로그, 환경 분리** 정책을 정의한다. 적용 법규:

- **개인정보보호법 (PIPA)** — 개인정보 접근 로그 5년 보존 의무
- **클라우드 보안인증 (CSAP)** — 격리·암호화·접근통제 표준
- **공공기관 정보보안 기본지침**
- **KORLINE/KOLIS-NET 데이터 교환 지침**

---

## 2. DB 사용자(Role) 분리

PostgreSQL Role 기반 RBAC. 사용자 ≠ 도서관 회원. 여기서의 사용자는 DB 접속 주체이다.

### 2.1 Role 계층

```
tulip_super        (BYPASSRLS, SUPERUSER 권한 일부)
  ├─ tulip_dba           (DDL, 백업, 모든 스키마)
  ├─ tulip_owner         (스키마 소유자, DDL)
  └─ tulip_app           (애플리케이션 부모 Role)
        ├─ tulip_app_rw        (운영 앱: SELECT/INSERT/UPDATE/DELETE)
        ├─ tulip_app_ro        (읽기전용 앱 / 통계 서비스)
        ├─ tulip_app_batch     (배치 작업자)
        └─ tulip_app_sip2      (SIP2 게이트웨이 — 제한적 쓰기)
  ├─ tulip_analyst       (분석가, 통계 read replica)
  ├─ tulip_auditor       (감사로그 read-only, PII 복호화 권한 분리)
  └─ tulip_backup        (REPLICATION 권한)
```

### 2.2 Role별 권한 정의 (DDL 예시)

```sql
-- 슈퍼관리자 (RLS BYPASS)
CREATE ROLE tulip_super NOLOGIN BYPASSRLS;

-- DBA (소유자급)
CREATE ROLE tulip_dba NOLOGIN CREATEDB CREATEROLE;
GRANT tulip_super TO tulip_dba;

-- 스키마 소유자
CREATE ROLE tulip_owner NOLOGIN;
ALTER SCHEMA tulip OWNER TO tulip_owner;

-- 애플리케이션 부모 Role
CREATE ROLE tulip_app NOLOGIN;
GRANT USAGE ON SCHEMA tulip TO tulip_app;

-- 앱 — 읽기/쓰기
CREATE ROLE tulip_app_rw LOGIN PASSWORD ':env:APP_RW_PWD' INHERIT;
GRANT tulip_app TO tulip_app_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tulip TO tulip_app_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tulip TO tulip_app_rw;
-- 향후 신규 테이블에도 자동 부여
ALTER DEFAULT PRIVILEGES IN SCHEMA tulip
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tulip_app_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA tulip
  GRANT USAGE, SELECT ON SEQUENCES TO tulip_app_rw;

-- 앱 — 읽기전용
CREATE ROLE tulip_app_ro LOGIN PASSWORD ':env:APP_RO_PWD' INHERIT;
GRANT tulip_app TO tulip_app_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA tulip TO tulip_app_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA tulip GRANT SELECT ON TABLES TO tulip_app_ro;

-- 배치
CREATE ROLE tulip_app_batch LOGIN PASSWORD ':env:BATCH_PWD' INHERIT;
GRANT tulip_app TO tulip_app_batch;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA tulip TO tulip_app_batch;

-- SIP2 게이트웨이 — 제한된 테이블만
CREATE ROLE tulip_app_sip2 LOGIN PASSWORD ':env:SIP2_PWD' INHERIT;
GRANT USAGE ON SCHEMA tulip TO tulip_app_sip2;
GRANT SELECT ON tlp_cmn_member, tlp_col_copy, tlp_cir_loan TO tulip_app_sip2;
GRANT INSERT, UPDATE ON tlp_cir_loan, tlp_cir_sip2_transaction TO tulip_app_sip2;

-- 분석가
CREATE ROLE tulip_analyst LOGIN PASSWORD ':env:ANALYST_PWD' INHERIT;
GRANT USAGE ON SCHEMA tulip TO tulip_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA tulip TO tulip_analyst;
-- PII 복호화 권한은 별도 함수 GRANT
REVOKE EXECUTE ON FUNCTION fn_decrypt_pii(BYTEA) FROM tulip_analyst;

-- 감사자
CREATE ROLE tulip_auditor LOGIN PASSWORD ':env:AUDITOR_PWD' INHERIT;
GRANT USAGE ON SCHEMA tulip TO tulip_auditor;
GRANT SELECT ON tlp_cmn_audit_log TO tulip_auditor;
-- 감사자는 일반 업무 테이블 PII 조회 시 마스킹 뷰만 사용 가능

-- 백업
CREATE ROLE tulip_backup LOGIN PASSWORD ':env:BACKUP_PWD' REPLICATION;
```

### 2.3 비밀번호·세션 정책

- DB 비밀번호: 환경변수 또는 Vault(HashiCorp/AWS Secrets Manager) 주입. 평문 저장 금지.
- 분기별 자동 로테이션 (애플리케이션 무중단).
- 세션 timeout: `idle_in_transaction_session_timeout = 60s`, `statement_timeout = 30s` (배치 Role은 별도).
- `pg_hba.conf` — `hostssl` 강제, IP allowlist + 비밀번호 + (옵션) 클라이언트 인증서.

---

## 3. 스키마별 권한 매트릭스

### 3.1 매트릭스

| 객체/Role | tulip_dba | tulip_app_rw | tulip_app_ro | tulip_app_batch | tulip_app_sip2 | tulip_analyst | tulip_auditor |
|---|---|---|---|---|---|---|---|
| 스키마 `tulip` USAGE | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CMN 모든 테이블 SELECT | ✅ | ✅ | ✅ | ✅ | 제한 | ✅(MASK) | 감사 only |
| CMN 모든 테이블 IUD | ✅ | ✅ | ✗ | ✅ | 일부 | ✗ | ✗ |
| CAT 모든 테이블 IUD | ✅ | ✅ | ✗ | ✅ | ✗ | ✗ | ✗ |
| COL 모든 테이블 IUD | ✅ | ✅ | ✗ | ✅ | ✗ | ✗ | ✗ |
| ACQ 모든 테이블 IUD | ✅ | ✅ | ✗ | ✅ | ✗ | ✗ | ✗ |
| CIR 모든 테이블 IUD | ✅ | ✅ | ✗ | ✅ | 제한 | ✗ | ✗ |
| ACS 모든 테이블 IUD | ✅ | ✅ | ✗ | ✅ | ✗ | ✗ | ✗ |
| FAC 모든 테이블 IUD | ✅ | ✅ | ✗ | ✅ | ✗ | ✗ | ✗ |
| 감사로그(audit_log) SELECT | ✅ | ✅(자기) | ✗ | ✗ | ✗ | ✗ | ✅ |
| 감사로그 IUD | ✅ | INSERT only | ✗ | ✗ | ✗ | ✗ | ✗ |
| PII 복호화 함수 EXECUTE | ✅ | ✅(감사) | ✗ | ✗ | ✗ | ✗ | ✅(특별승인) |
| DDL (CREATE/ALTER) | ✅ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| RLS BYPASS | ✅(super) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

### 3.2 운영 원칙

- **앱은 RLS BYPASS 없음** — JWT의 `tenant_id`를 세션 변수로 전달하여 RLS가 자연스럽게 격리.
- **DBA만 BYPASSRLS** — 일상 운영도 가능한 한 `SET ROLE`로 권한 강등 후 작업.
- **권한 변경은 DBA가 실행**, DevLead 요청서 기반 — `tlp_cmn_audit_log`에 기록.
- **신규 직원 입사·퇴사** 시 Role 부여/회수 절차 표준화.

---

## 4. RLS (Row Level Security) 활성화 목록

### 4.1 RLS 적용 정책 유형

| 정책 명 | 조건 | 적용 테이블 |
|---|---|---|
| `pol_tenant_iso` | `tenant_id = fn_current_tenant_id() OR tenant_id = 0` | 모든 업무 테이블 |
| `pol_library_iso` | `library_id = ANY(fn_current_user_libraries())` | 관 단위 권한 적용 테이블 |
| `pol_pii_view` | `current_role IN ('tulip_app_rw','tulip_dba')` | PII 컬럼 뷰 |
| `pol_audit_iso` | `tenant_id = fn_current_tenant_id()` (감사자는 자기 테넌트만) | 감사로그 |

### 4.2 RLS 활성화 대상 테이블 (전체)

| 도메인 | 테이블 |
|---|---|
| CMN | tlp_cmn_member, tlp_cmn_member_status_history, tlp_cmn_member_consent, tlp_cmn_user_role, tlp_cmn_policy, tlp_cmn_policy_rule, tlp_cmn_notification_log, tlp_cmn_audit_log, tlp_cmn_location, tlp_cmn_shelf, tlp_cmn_role, tlp_cmn_library, (tlp_cmn_tenant은 슈퍼만) |
| CAT | tlp_cat_bibliography, tlp_cat_marc_field, tlp_cat_marc_record_raw, tlp_cat_authority, tlp_cat_bib_change_log, tlp_cat_z3950_server, tlp_cat_kolis_sync_log |
| COL | tlp_col_holding, tlp_col_copy, tlp_col_accession_rule, tlp_col_item_status_history, tlp_col_inventory, tlp_col_transfer, tlp_col_withdrawal |
| ACQ | tlp_acq_request, tlp_acq_vendor, tlp_acq_purchase_order, tlp_acq_purchase_order_item, tlp_acq_receipt, tlp_acq_budget, tlp_acq_budget_transaction, tlp_acq_donation, tlp_acq_serial_subscription, tlp_acq_serial_issue |
| CIR | tlp_cir_loan, tlp_cir_hold, tlp_cir_fine, tlp_cir_fine_payment, tlp_cir_lost_damaged_report, tlp_cir_member_block, tlp_cir_ill_request, tlp_cir_sip2_transaction, tlp_cir_opac_search_log |
| ACS | tlp_acs_gate, tlp_acs_access_event, tlp_acs_eas_alarm, tlp_acs_temp_pass, tlp_acs_security_event |
| FAC | tlp_fac_seat, tlp_fac_seat_reservation, tlp_fac_room, tlp_fac_room_reservation, tlp_fac_facility_issue |

**RLS 비활성 (전 테넌트 공유)**: `tlp_cmn_code_group`, `tlp_cmn_code` (tenant_id=0 공유 부분), `tlp_cmn_classification`, `tlp_cmn_permission`.

### 4.3 RLS 우회 절차 (운영 점검·통계)

```sql
-- 슈퍼관리자가 통계 작업 시
SET ROLE tulip_super;
-- 작업 후
RESET ROLE;
```

- BYPASS 사용 시 자동 audit_log 기록 (트리거).

---

## 5. 컬럼 암호화 정책

### 5.1 암호화 대상 컬럼

| 테이블.컬럼 | 등급 | 알고리즘 | 비고 |
|---|---|---|---|
| `tlp_cmn_member.name_enc` | 1급 | pgcrypto `pgp_sym_encrypt` (AES-256) | + name_hash(검색) |
| `tlp_cmn_member.phone_enc` | 2급 | 동일 | + phone_hash(검색) |
| `tlp_cmn_member.address_enc` | 2급 | 동일 | |
| `tlp_cmn_member.ci_enc` | 1급 | 동일 | 본인확인 CI |
| `tlp_cmn_member.password_hash` | 1급 | BCrypt (단방향) | |
| `tlp_acq_donation.donor_name_enc` | 2급 | pgp_sym_encrypt | |
| `tlp_acs_temp_pass.visitor_name_enc` | 2급 | 동일 | |
| `tlp_acs_temp_pass.visitor_contact_enc` | 2급 | 동일 | |
| 가족·단체회원 가족정보 | 2급 | 동일 | (CMN-017) |

### 5.2 키 관리(KMS)

- **DEK(Data Encryption Key)**: pgcrypto가 사용 — DB 외부 KMS에 보관, 애플리케이션 시작 시 주입.
- **KEK(Key Encryption Key)**: AWS KMS / HashiCorp Vault.
- **분기별 키 교체** — Re-encrypt 배치 절차 필요.
- 키 위치 옵션:
  1. `current_setting('app.pii_key')` — 세션 시작 시 SET (단, 메모리 노출 위험)
  2. 외부 PEP(Policy Enforcement Point)에서 복호화 — DB는 BYTEA만 저장
  3. PostgreSQL TDE (외부 솔루션, Y2 검토)

### 5.3 암호화 함수 패턴

```sql
-- 암호화 (애플리케이션에서 호출)
CREATE OR REPLACE FUNCTION fn_encrypt_pii(plain TEXT)
RETURNS BYTEA AS $$
  SELECT pgp_sym_encrypt(plain, current_setting('app.pii_key', true));
$$ LANGUAGE SQL STABLE;

-- 복호화 (제한된 Role만 EXECUTE)
CREATE OR REPLACE FUNCTION fn_decrypt_pii(cipher BYTEA)
RETURNS TEXT AS $$
  SELECT pgp_sym_decrypt(cipher, current_setting('app.pii_key', true));
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION fn_decrypt_pii FROM PUBLIC;
GRANT EXECUTE ON FUNCTION fn_decrypt_pii TO tulip_app_rw;

-- 검색용 해시
CREATE OR REPLACE FUNCTION fn_hash_pii(plain TEXT)
RETURNS VARCHAR AS $$
  SELECT encode(digest(plain || current_setting('app.pii_salt'), 'sha256'), 'hex');
$$ LANGUAGE SQL IMMUTABLE;
```

### 5.4 PII 접근 감사 로그

- 모든 PII 복호화는 `tlp_cmn_audit_log`에 자동 기록 (트리거 또는 wrapper 함수).
- 감사 항목: `action='PII_DECRYPT'`, `target_resource`, `target_id`, `actor_member_id`, `ip_address`, `trace_id`.
- 5년 보존 (PIPA 의무).

---

## 6. 마스킹 정책 (View / Function)

### 6.1 마스킹 뷰

운영 SELECT 쿼리는 원본 테이블 대신 마스킹 뷰 사용 권장.

```sql
CREATE OR REPLACE VIEW vw_cmn_member_masked AS
SELECT
  m.id,
  m.tenant_id,
  m.public_id,
  m.member_no,
  -- 이름: 앞 1자 + ** (예: 홍**)
  CASE
    WHEN current_setting('app.pii_unmask', true) = 'true'
      THEN fn_decrypt_pii(m.name_enc)
    ELSE substring(fn_decrypt_pii(m.name_enc), 1, 1) || repeat('*', 2)
  END AS name,
  -- 전화: 010-****-1234
  CASE
    WHEN current_setting('app.pii_unmask', true) = 'true'
      THEN fn_decrypt_pii(m.phone_enc)
    ELSE regexp_replace(fn_decrypt_pii(m.phone_enc), '(\d{3})-?(\d{4})-?(\d{4})', '\1-****-\3')
  END AS phone,
  -- 이메일: ab***@example.com
  regexp_replace(m.email, '^(.{2}).*(@.*)$', '\1***\2') AS email,
  m.member_grade, m.status, m.join_date, m.expire_date
FROM tlp_cmn_member m;

GRANT SELECT ON vw_cmn_member_masked TO tulip_app_ro, tulip_analyst;
```

### 6.2 언마스킹 절차

- 사서·관장이 회원 정보 전체 조회 필요 시 → 별도 화면 + `SET LOCAL app.pii_unmask = 'true'`
- 동시에 `tlp_cmn_audit_log`에 사유·대상 기록 의무.
- DevLead와 정합: 화면 단위 권한 검사 후 세션 변수 설정.

### 6.3 마스킹 대상 매트릭스

| 컬럼 | 평문 (사서) | 마스킹 (분석/외부) |
|---|---|---|
| 회원명 | 홍길동 | 홍** |
| 전화 | 010-1234-5678 | 010-****-5678 |
| 이메일 | abc@x.com | ab***@x.com |
| 주소 | 서울시 강남구 ... 101호 | 서울시 강남구 *** |
| 생년월일 | 1990-01-01 | 1990-**-** |
| CI/DI | (복호화 불가) | - |

---

## 7. 감사 로그 정책

### 7.1 감사 대상

| 분류 | 대상 액션 | 적재 위치 |
|---|---|---|
| 인증 | LOGIN/LOGOUT/LOGIN_FAIL | tlp_cmn_audit_log |
| 권한 | ROLE_GRANT/ROLE_REVOKE | tlp_cmn_audit_log |
| PII 접근 | PII_VIEW/PII_DECRYPT/PII_EXPORT | tlp_cmn_audit_log |
| 회원 변경 | MEMBER_CREATE/UPDATE/DELETE | tlp_cmn_audit_log + member_status_history |
| 정책 변경 | POLICY_CHANGE | tlp_cmn_audit_log + policy_history |
| 서지 변경 | BIB_CREATE/UPDATE/DELETE/MERGE/SPLIT | bib_change_log |
| 자료 상태 | COPY_STATUS_CHANGE | item_status_history |
| 출입 | (이미 access_event) | access_event |
| 보안 | THEFT_ALARM/UNAUTH_ENTRY | security_event |
| DB 직접접근 | pgAudit | 별도 syslog |

### 7.2 적재 구조 (요약)

```sql
-- 감사 로그 (재인용)
tlp_cmn_audit_log (
  id, tenant_id, actor_member_id, actor_role,
  action, target_resource, target_id,
  before_value JSONB, after_value JSONB,
  ip_address INET, user_agent, trace_id,
  acted_at TIMESTAMPTZ
);
```

### 7.3 변경/접근 로그 분리

- **변경 로그**: 데이터 IUD 변경 사실 (before/after).
- **접근 로그**: PII SELECT, EXPORT 행위 (변경 없음).
- 두 로그 모두 동일 테이블에 적재하되 `action` 필드로 구분.
- 변경 로그는 트리거 자동 적재, 접근 로그는 애플리케이션 explicit 호출.

### 7.4 pgAudit (DB 차원 감사)

```ini
# postgresql.conf
shared_preload_libraries = 'pgaudit, pg_stat_statements'
pgaudit.log = 'role, ddl, write'
pgaudit.log_relation = on
pgaudit.log_parameter = off  -- PII 노출 방지
```

- DDL·Role 변경·Write 명령 syslog 적재.
- 별도 SIEM(보안관제 시스템)으로 전송 (DevLead/PM 협의).

### 7.5 보존 정책

| 로그 종류 | 보존 | 비고 |
|---|---|---|
| PII 접근 로그 | 5년 | PIPA 의무 |
| 권한 변경 로그 | 5년 | |
| 인증 로그 | 1년 | |
| 일반 변경 로그 | 3년 | |
| 출입 이벤트 | 5년 | (Planner 비기능 요구사항) |
| 보안 이벤트 | 5년 | |

---

## 8. 환경 분리 정책

### 8.1 환경 구성

| 환경 | 용도 | 데이터 |
|---|---|---|
| Production | 운영 | 실데이터, 격리 |
| Staging | UAT, 배포 전 검증 | 운영 익명화 데이터 (월 1회 갱신) |
| Development | 개발 | 합성 데이터 + 매우 제한된 익명화 샘플 |
| QA Test | 자동 테스트 | 합성 데이터 + 픽스처 |

### 8.2 환경 간 데이터 이동 정책

- **운영 → 스테이징**: 익명화 후 이전 (개인정보 파기 또는 가명처리).
- **운영 → 개발**: **원칙적으로 금지**, 합성 데이터 사용.
- **운영 데이터 다운로드**: PM·DBA 공동 승인 필요. 감사로그 기록.
- 모든 환경 별도 KMS 키 — 키 교차 사용 금지.

### 8.3 익명화/가명처리 절차

```sql
-- 회원 익명화 (운영 → 스테이징 이전 시)
UPDATE tlp_cmn_member SET
  name_enc      = fn_encrypt_pii('Anonymous_' || id),
  phone_enc     = fn_encrypt_pii('010-0000-' || lpad((id % 10000)::text, 4, '0')),
  email         = 'anon_' || id || '@example.local',
  email_hash    = fn_hash_pii('anon_' || id || '@example.local'),
  address_enc   = fn_encrypt_pii('익명주소'),
  ci_enc        = NULL,
  sso_provider  = NULL,
  sso_subject   = NULL;

-- 단순 무작위화는 PIPA 가명처리 요건에 미달할 수 있음 — 법무 검토 필요
```

### 8.4 회원 탈퇴 5년 경과 익명화

- 배치 작업: 매일 새벽 `WITHDRAWN AND deleted_at < now() - INTERVAL '5 years'` 회원 익명화.
- 익명화 후 분리 가능 불가능한 컬럼은 NULL 처리.
- 익명화 완료 회원은 `is_anonymized = true` 표시.

---

## 9. 네트워크 / 접속 보안

| 항목 | 정책 |
|---|---|
| TLS | 모든 접속 TLS 1.2+ 강제 (`hostssl`) |
| IP allowlist | `pg_hba.conf`로 앱 서버·관리 bastion만 허용 |
| 클라이언트 인증서 | DBA·백업 Role은 mTLS |
| 직접 DB 접속 | 운영 DB는 bastion 경유 + 2FA, 감사로그 |
| 슈퍼유저 비밀번호 | KMS 보관, 분기 교체 |
| `listen_addresses` | 사설 IP만 |
| ACL | 별도 보안그룹 (인프라 계층) |

---

## 10. 권한 관리 운영 절차

### 10.1 권한 부여 요청 절차

1. **요청자**: DevLead (또는 PM 승인)
2. **요청 양식**: 권한 요청서 (대상 Role, 대상 객체, 사유, 만료일)
3. **DBA 검토·실행**: SQL 작성·실행, audit_log 적재
4. **회수**: 만료일 자동 회수 또는 수동 회수
5. **관리 대장 갱신**: `DB 권한 관리 대장` 갱신

### 10.2 권한 관리 대장 (Excel/Notion)

| 항목 | 내용 |
|---|---|
| 요청일 / 요청자 / 승인자 |
| Role 이름 / 권한 종류 / 대상 객체 |
| 부여일 / 만료일 / 회수일 |
| 사유 / 비고 |

### 10.3 정기 권한 감사

- 분기 1회 모든 Role 권한 목록 추출, DevLead/PM과 점검.
- 미사용 Role(`pg_stat_user_tables` 분석) 회수.
- 퇴사자 계정 즉시 회수 — 인사 시스템 연동 (Y2).

---

## 11. 보안 사고 대응

### 11.1 사고 유형·대응

| 유형 | 대응 |
|---|---|
| PII 유출 의심 | 즉시 PM·DevLead 통지 → 감사로그 분석 → 영향 범위 파악 → PIPA 신고 의무 검토 |
| DB 무단 접근 | bastion 로그 + pgAudit 분석 → 해당 Role 즉시 차단 |
| SQL Injection 의심 | 애플리케이션 로그 + pg_stat_statements 패턴 분석 |
| 백업 매체 분실 | 암호화 키 즉시 교체 + 회수 절차 |
| 키 유출 | KMS 즉시 rotate → DEK 전체 재암호화 (단계적) |

### 11.2 보고 책임

- **DBA → PM (즉시 통지)**: 사고 발생 1시간 이내.
- **PM → 고객·규제 기관**: 법정 기한 (PIPA 24시간 / 72시간).
- **DevLead 협력**: 애플리케이션 계층 점검.

---

## 12. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v0.1 | 2026-05-11 | DBA Agent | Role 7개 분리, RLS 정책 정의, pgcrypto + KMS 컬럼 암호화, 마스킹 뷰, 5년 PII 감사로그, 환경 분리·익명화 절차 수립 |
