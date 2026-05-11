# 마스터 ERD (Master ERD)

| 항목 | 내용 |
|---|---|
| 문서명 | 마스터 ERD |
| 문서 ID | DBA-02 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DBA Agent |
| 검토자 | DevLead, BackendSenior |
| 상태 | 초안 |
| 대상 DBMS | PostgreSQL 15+ |

---

## 1. 문서 개요

본 문서는 Tulip+ 도서관통합관리시스템의 **도메인별 데이터 모델**을 ERD(Mermaid `erDiagram`)로 표현한다. Planner 6개 도메인 요구사항 + 공통(CMN)에서 도출된 ~120개 엔티티(총 7개 도메인)를 다룬다.

### 1.1 표기 규약

- 카디널리티: `||--o{`(1:N), `||--||`(1:1), `}o--o{`(N:M)
- 필수 컬럼: `NOT NULL` (생략 표기), 선택: `nullable`
- PK: `PK`, FK: `FK`, UNIQUE: `UK`
- 모든 엔티티는 공통 컬럼(`tenant_id`, `library_id`, `created_at`, ...) 보유 — ERD에서는 핵심 컬럼만 발췌
- 도메인 약어: CMN/ACQ/CAT/CIR/COL/ACS/FAC
- 도메인 간 FK는 도메인 경계도(`§10`)에 별도 표기

### 1.2 식별 엔티티 총괄

| 도메인 | 엔티티 수 | 핵심 엔티티 |
|---|---|---|
| CMN | 22 | tenant, library, member, role, code, policy, audit_log |
| CAT | 13 | bibliography, marc_field, authority, classification |
| COL | 13 | holding, copy, inventory, transfer, withdrawal |
| ACQ | 16 | acq_request, vendor, purchase_order, budget, donation, serial |
| CIR | 16 | loan, hold, fine, lost_damaged, ill_request, sip2_txn |
| ACS | 9 | gate, access_event, eas_alarm, temp_pass, security_event |
| FAC | 11 | seat, seat_reservation, room, room_reservation, issue |
| **합계** | **100** | — |

---

## 2. CMN — 공통/플랫폼 도메인

```mermaid
erDiagram
    TENANT ||--o{ LIBRARY : has
    TENANT ||--o{ MEMBER : has
    TENANT ||--o{ ROLE : has
    TENANT ||--o{ POLICY : has
    TENANT ||--o{ SUBSCRIPTION_PLAN : has
    TENANT ||--o{ CODE : extends

    LIBRARY ||--o{ LIBRARY_CALENDAR : has
    LIBRARY ||--o{ LOCATION : has
    LIBRARY ||--o{ SHELF : has

    MEMBER ||--o{ MEMBER_CARD : owns
    MEMBER }o--|| MEMBER_TYPE : classified_as
    MEMBER ||--o{ MEMBER_STATUS_HISTORY : has
    MEMBER ||--o{ MEMBER_CONSENT : has
    MEMBER ||--o{ USER_ROLE : assigned

    ROLE ||--o{ ROLE_PERMISSION : grants
    PERMISSION ||--o{ ROLE_PERMISSION : included_in
    MEMBER ||--o{ USER_ROLE : has
    ROLE ||--o{ USER_ROLE : assigned_to

    CODE_GROUP ||--o{ CODE : contains
    CODE ||--o{ CODE_I18N : translated
    CLASSIFICATION ||--o{ CLASSIFICATION : parent

    POLICY ||--o{ POLICY_RULE : rules
    POLICY ||--o{ POLICY_HISTORY : history

    NOTIFICATION_TEMPLATE ||--o{ NOTIFICATION_LOG : used_by

    TENANT {
        bigint id PK
        varchar tenant_code UK
        varchar tenant_name
        varchar plan_code FK
        varchar status
        date subscription_from
        date subscription_to
    }
    LIBRARY {
        bigint id PK
        bigint tenant_id FK
        bigint parent_library_id FK "본관-분관"
        varchar library_code UK
        varchar library_name
        varchar branch_type "MAIN|BRANCH|MOBILE"
        varchar address
        boolean is_integrated_loan "다관 통합대출 여부"
    }
    LIBRARY_CALENDAR {
        bigint id PK
        bigint library_id FK
        date calendar_date
        varchar day_type "OPEN|CLOSED|HOLIDAY|SPECIAL"
        time open_time
        time close_time
    }
    LOCATION {
        bigint id PK
        bigint library_id FK
        varchar location_code
        varchar location_name
        varchar location_type "STACK|READING|RARE|CLOSED"
    }
    SHELF {
        bigint id PK
        bigint location_id FK
        varchar shelf_code
        varchar call_no_range_from
        varchar call_no_range_to
    }
    MEMBER {
        bigint id PK
        bigint tenant_id FK
        ulid public_id UK
        varchar member_no UK
        varchar name_enc "암호화"
        varchar phone_enc "암호화"
        varchar email
        varchar email_hash "검색용"
        varchar address_enc "암호화"
        varchar ci_enc "본인인증 CI"
        bigint member_type_id FK
        varchar member_grade "REGULAR|ASSOCIATE"
        varchar status "ACTIVE|DORMANT|SUSPENDED|WITHDRAWN"
        date join_date
        date expire_date
    }
    MEMBER_TYPE {
        bigint id PK
        bigint tenant_id FK
        varchar type_code
        varchar type_name
        varchar applies_to "PUBLIC|UNIV|SCHOOL"
    }
    MEMBER_CARD {
        bigint id PK
        bigint member_id FK
        varchar card_no UK
        varchar card_type "BARCODE|IC|QR|MOBILE"
        varchar status
        date issued_date
        date expire_date
    }
    MEMBER_STATUS_HISTORY {
        bigint id PK
        bigint member_id FK
        varchar from_status
        varchar to_status
        varchar reason
        timestamptz changed_at
    }
    MEMBER_CONSENT {
        bigint id PK
        bigint member_id FK
        varchar consent_type "COLLECT|USE|3RDPARTY|MARKETING"
        boolean is_granted
        timestamptz granted_at
        timestamptz revoked_at
    }
    ROLE {
        bigint id PK
        bigint tenant_id FK
        varchar role_code UK
        varchar role_name
        varchar role_scope "PLATFORM|TENANT|LIBRARY"
    }
    PERMISSION {
        bigint id PK
        varchar permission_code UK
        varchar resource
        varchar action
    }
    ROLE_PERMISSION {
        bigint role_id PK
        bigint permission_id PK
    }
    USER_ROLE {
        bigint id PK
        bigint member_id FK
        bigint role_id FK
        bigint library_id FK "관 한정 (NULL=전체)"
        date valid_from
        date valid_to
    }
    CODE_GROUP {
        varchar group_code PK
        varchar group_name
        text description
    }
    CODE {
        bigint id PK
        bigint tenant_id FK "0=공유"
        varchar group_code FK
        varchar code
        varchar code_name
        int sort_order
        jsonb extra
    }
    CODE_I18N {
        bigint code_id PK
        varchar locale PK
        varchar label
    }
    CLASSIFICATION {
        bigint id PK
        varchar scheme "KDC|DDC|LC|UDC"
        varchar class_code
        varchar class_name
        int level
        bigint parent_id FK
    }
    POLICY {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK "NULL=테넌트 공통"
        varchar policy_type "LOAN|HOLD|FINE|ACCESS|FACILITY"
        varchar policy_name
        date effective_from
        date effective_to
        int priority
    }
    POLICY_RULE {
        bigint id PK
        bigint policy_id FK
        jsonb conditions "member_type,item_type,..."
        jsonb actions "loan_limit,loan_days,fine_amount,..."
    }
    POLICY_HISTORY {
        bigint id PK
        bigint policy_id FK
        jsonb before_value
        jsonb after_value
        timestamptz changed_at
    }
    SUBSCRIPTION_PLAN {
        bigint id PK
        varchar plan_code UK
        varchar plan_name
        jsonb features
        numeric monthly_fee
    }
    NOTIFICATION_TEMPLATE {
        bigint id PK
        bigint tenant_id FK
        varchar template_code
        varchar channel "EMAIL|SMS|KAKAO|PUSH"
        varchar locale
        varchar subject
        text body_template
    }
    NOTIFICATION_LOG {
        bigint id PK
        bigint tenant_id FK
        bigint member_id FK
        bigint template_id FK
        varchar channel
        varchar status "QUEUED|SENT|FAILED|READ"
        timestamptz sent_at
    }
    AUDIT_LOG {
        bigint id PK
        bigint tenant_id FK
        bigint actor_member_id FK
        varchar action
        varchar target_resource
        bigint target_id
        jsonb before_value
        jsonb after_value
        varchar ip_address
        timestamptz acted_at
    }
```

### 2.1 CMN 엔티티 목록 (22)

tenant, library, library_calendar, location, shelf, member, member_type, member_card, member_status_history, member_consent, role, permission, role_permission, user_role, code_group, code, code_i18n, classification, policy, policy_rule, policy_history, subscription_plan, notification_template, notification_log, audit_log.

---

## 3. CAT — 목록(Cataloging) 도메인

```mermaid
erDiagram
    BIBLIOGRAPHY ||--o{ MARC_FIELD : composed_of
    BIBLIOGRAPHY ||--o{ MARC_RECORD_RAW : has_raw
    BIBLIOGRAPHY ||--o{ BIB_CLASSIFICATION : classified
    BIBLIOGRAPHY ||--o{ BIB_SUBJECT : subjected
    BIBLIOGRAPHY ||--o{ BIB_AUTHORITY_LINK : linked
    BIBLIOGRAPHY ||--o{ BIB_CHANGE_LOG : history
    BIBLIOGRAPHY ||--o{ BIB_INDEX_TSV : indexed_by

    AUTHORITY ||--o{ AUTHORITY_VARIANT : has_form
    AUTHORITY ||--o{ BIB_AUTHORITY_LINK : referenced
    CLASSIFICATION ||--o{ BIB_CLASSIFICATION : referenced

    Z3950_SERVER ||--o{ EXTERNAL_FETCH_LOG : queried
    KOLIS_SYNC_LOG ||--o{ BIBLIOGRAPHY : synced

    BIBLIOGRAPHY {
        bigint id PK
        bigint tenant_id FK
        ulid public_id UK
        varchar bib_status "DRAFT|PUBLISHED|HIDDEN|MERGED|DELETED"
        varchar marc_format "KORMARC|MARC21"
        varchar leader VARCHAR(24)
        varchar material_type "BK|SE|MX|MU|VM|CR|ER"
        varchar language
        varchar title_main
        varchar title_sort
        varchar author_main
        varchar publisher
        varchar pub_year
        varchar isbn
        varchar issn
        bigint merged_into_id FK "결합된 대상"
    }
    MARC_FIELD {
        bigint id PK
        bigint bibliography_id FK
        varchar tag VARCHAR(3) "020,245,700..."
        char ind1
        char ind2
        smallint occurrence_no
        char field_type "C|D"
        text control_value
        jsonb subfields "[{code,value}]"
    }
    MARC_RECORD_RAW {
        bigint id PK
        bigint bibliography_id FK
        varchar source "Z3950|KOLIS|KERIS|IMPORT|MANUAL"
        varchar source_id
        text raw_marc
        varchar format "ISO2709|MARCXML|JSON"
        timestamptz fetched_at
    }
    AUTHORITY {
        bigint id PK
        bigint tenant_id FK
        varchar auth_type "PERSON|CORP|MEETING|UNIFORM_TITLE|SUBJECT|SERIES"
        varchar heading_main
        varchar heading_sort
        jsonb marc_data
    }
    AUTHORITY_VARIANT {
        bigint id PK
        bigint authority_id FK
        varchar variant_type "SEE|SEE_ALSO"
        varchar heading
    }
    BIB_AUTHORITY_LINK {
        bigint id PK
        bigint bibliography_id FK
        bigint authority_id FK
        varchar field_tag
        smallint occurrence_no
    }
    BIB_CLASSIFICATION {
        bigint id PK
        bigint bibliography_id FK
        bigint classification_id FK
        varchar class_code
        varchar scheme "KDC|DDC|LC"
        boolean is_primary
    }
    BIB_SUBJECT {
        bigint id PK
        bigint bibliography_id FK
        varchar subject_heading
        varchar scheme "LCSH|KSH|NDLSH"
    }
    BIB_INDEX_TSV {
        bigint bibliography_id PK
        tsvector tsv_title
        tsvector tsv_author
        tsvector tsv_subject
        tsvector tsv_full
    }
    BIB_CHANGE_LOG {
        bigint id PK
        bigint bibliography_id FK
        bigint changed_by FK
        char op_type "I|U|D|M|S"
        jsonb before_value
        jsonb after_value
        text reason
        timestamptz op_at
    }
    Z3950_SERVER {
        bigint id PK
        bigint tenant_id FK
        varchar server_code
        varchar server_name
        varchar host
        int port
        varchar database
        varchar charset
        int timeout_ms
    }
    EXTERNAL_FETCH_LOG {
        bigint id PK
        bigint tenant_id FK
        bigint server_id FK
        varchar query
        int result_count
        int duration_ms
        varchar status
        timestamptz fetched_at
    }
    KOLIS_SYNC_LOG {
        bigint id PK
        bigint tenant_id FK
        varchar sync_type "UPLOAD|DOWNLOAD"
        int record_count
        int success_count
        int error_count
        text error_summary
        timestamptz synced_at
    }
```

### 3.1 CAT 엔티티 목록 (13)

bibliography, marc_field, marc_record_raw, authority, authority_variant, bib_authority_link, bib_classification, bib_subject, bib_index_tsv, bib_change_log, z3950_server, external_fetch_log, kolis_sync_log.

---

## 4. COL — 장서(Collection) 도메인

```mermaid
erDiagram
    BIBLIOGRAPHY ||--o{ HOLDING : has
    LIBRARY ||--o{ HOLDING : owns
    HOLDING ||--o{ COPY : has
    LOCATION ||--o{ COPY : located_in
    SHELF ||--o{ COPY : shelved_on

    COPY ||--o{ ITEM_STATUS_HISTORY : has
    COPY ||--o{ ITEM_LOCATION_HISTORY : has
    COPY ||--o{ TRANSFER : transferred
    COPY ||--o{ WITHDRAWAL : withdrawn
    COPY ||--o{ INVENTORY_SCAN : scanned
    COPY ||--o{ RARE_ITEM_DETAIL : detailed

    ACCESSION_RULE ||--o{ COPY : numbered_by

    INVENTORY ||--o{ INVENTORY_SCAN : scans
    INVENTORY ||--o{ INVENTORY_REPORT : reports

    WITHDRAWAL ||--o{ WITHDRAWAL_APPROVAL : approved_by

    HOLDING {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint bibliography_id FK
        varchar call_no
        int total_copies
        int available_copies
        varchar holding_status
    }
    COPY {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint holding_id FK
        bigint location_id FK
        bigint shelf_id FK
        varchar accession_no UK "관 단위 유일"
        varchar barcode UK
        varchar rfid_uid UK
        varchar call_no
        varchar volume "권차"
        varchar copy_no "복본"
        varchar item_type "BK|SE|..."
        varchar item_status "AVAILABLE|ON_LOAN|RESERVED|LOST|DAMAGED|REPAIR|WITHDRAWN|IN_TRANSIT|INVENTORY"
        numeric purchase_price
        date acquired_date
        varchar acquired_method "PURCHASE|DONATION|EXCHANGE"
        boolean is_lendable
        boolean is_rare
    }
    ACCESSION_RULE {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar item_type
        varchar prefix
        varchar year_part "YYYY|YY|NONE"
        int seq_width
        bigint current_seq
    }
    ITEM_STATUS_HISTORY {
        bigint id PK
        bigint copy_id FK
        varchar from_status
        varchar to_status
        varchar reason_code
        text reason_text
        bigint changed_by FK
        timestamptz changed_at
    }
    ITEM_LOCATION_HISTORY {
        bigint id PK
        bigint copy_id FK
        bigint from_location_id FK
        bigint to_location_id FK
        timestamptz moved_at
    }
    INVENTORY {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar inventory_name
        bigint location_id FK "범위"
        varchar class_range_from
        varchar class_range_to
        date plan_from
        date plan_to
        varchar status "PLANNED|RUNNING|DONE|CANCELED"
    }
    INVENTORY_SCAN {
        bigint id PK
        bigint inventory_id FK
        bigint copy_id FK
        varchar scanned_code
        varchar result "NORMAL|MISSING|MISSHELVED|UNEXPECTED"
        bigint scanner_user_id FK
        timestamptz scanned_at
    }
    INVENTORY_REPORT {
        bigint id PK
        bigint inventory_id FK
        int normal_count
        int missing_count
        int misshelved_count
        int unexpected_count
        timestamptz reported_at
    }
    TRANSFER {
        bigint id PK
        bigint tenant_id FK
        bigint copy_id FK
        bigint from_library_id FK
        bigint to_library_id FK
        bigint from_shelf_id FK
        bigint to_shelf_id FK
        varchar transfer_type "INTER_LIBRARY|INTRA_SHELF|RESHELVE"
        varchar status "REQUESTED|APPROVED|IN_TRANSIT|RECEIVED|CANCELED"
        timestamptz requested_at
        timestamptz received_at
    }
    WITHDRAWAL {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint copy_id FK
        varchar reason_code "DAMAGED|LOST|OBSOLETE|DUPLICATE|DONATION_OUT|SALE"
        text reason_text
        varchar disposal_method "DISCARD|DONATE|SELL|RECYCLE"
        varchar status "REQUESTED|APPROVED|EXECUTED|CANCELED"
        bigint requested_by FK
        timestamptz requested_at
        timestamptz executed_at
    }
    WITHDRAWAL_APPROVAL {
        bigint id PK
        bigint withdrawal_id FK
        int step_no
        bigint approver_id FK
        varchar decision "APPROVED|REJECTED|HOLD"
        text comment
        timestamptz decided_at
    }
    RARE_ITEM_DETAIL {
        bigint copy_id PK
        varchar acquisition_source
        date original_pub_date
        text condition_note
        varchar access_restriction
        boolean photocopy_allowed
    }
```

### 4.1 COL 엔티티 목록 (13)

holding, copy, accession_rule, item_status_history, item_location_history, inventory, inventory_scan, inventory_report, transfer, withdrawal, withdrawal_approval, rare_item_detail, (preservation_log Y2).

---

## 5. ACQ — 수서(Acquisition) 도메인

```mermaid
erDiagram
    ACQ_REQUEST ||--o{ ACQ_REQUEST_APPROVAL : approved_by
    ACQ_REQUEST }o--|| MEMBER : requested_by

    PURCHASE_ORDER ||--o{ PURCHASE_ORDER_ITEM : has
    PURCHASE_ORDER ||--o{ PURCHASE_ORDER_APPROVAL : approved_by
    PURCHASE_ORDER }o--|| VENDOR : ordered_to
    PURCHASE_ORDER_ITEM ||--o{ RECEIPT_ITEM : received_via
    PURCHASE_ORDER_ITEM }o--|| ACQ_REQUEST : fulfills
    PURCHASE_ORDER_ITEM }o--o| BIBLIOGRAPHY : refers

    RECEIPT ||--o{ RECEIPT_ITEM : has
    RECEIPT_ITEM ||--o{ COPY : creates
    RECEIPT ||--o{ RECEIPT_INVOICE : invoiced

    BUDGET ||--o{ BUDGET_ALLOCATION : split
    BUDGET ||--o{ BUDGET_TRANSACTION : transacted
    BUDGET_ALLOCATION ||--o{ BUDGET_TRANSACTION : drawn

    DONATION ||--o{ DONATION_ITEM : contains
    DONATION_ITEM ||--o| COPY : becomes

    SERIAL_SUBSCRIPTION ||--o{ SERIAL_ISSUE : expects
    SERIAL_ISSUE ||--o| COPY : becomes

    ACQ_REQUEST {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint member_id FK
        varchar source "OPAC|STAFF|BULK"
        varchar title
        varchar author
        varchar isbn
        varchar publisher
        varchar pub_year
        numeric expected_price
        varchar status "SUBMITTED|REVIEWING|APPROVED|REJECTED|ORDERED|RECEIVED|CLOSED"
        text reject_reason
    }
    ACQ_REQUEST_APPROVAL {
        bigint id PK
        bigint request_id FK
        int step_no
        bigint approver_id FK
        varchar decision
        timestamptz decided_at
    }
    VENDOR {
        bigint id PK
        bigint tenant_id FK
        varchar vendor_code UK
        varchar vendor_name
        varchar business_no
        varchar contact_name
        varchar contact_phone
        varchar contact_email
        numeric default_discount_rate
        varchar payment_terms
        varchar status
    }
    PURCHASE_ORDER {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint vendor_id FK
        varchar order_no UK
        varchar order_type "PURCHASE|BID|AGENT"
        date order_date
        numeric total_amount
        varchar currency
        numeric fx_rate
        varchar status "DRAFT|APPROVED|SENT|PARTIAL|RECEIVED|CANCELED"
    }
    PURCHASE_ORDER_ITEM {
        bigint id PK
        bigint order_id FK
        bigint acq_request_id FK
        bigint bibliography_id FK
        varchar title
        varchar isbn
        int order_qty
        int received_qty
        numeric unit_price
        numeric discount_rate
        bigint budget_allocation_id FK
    }
    PURCHASE_ORDER_APPROVAL {
        bigint id PK
        bigint order_id FK
        int step_no
        bigint approver_id FK
        varchar decision
        timestamptz decided_at
    }
    RECEIPT {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint order_id FK
        varchar receipt_no UK
        date receipt_date
        varchar status "DRAFT|INSPECTING|COMPLETED|REJECTED"
    }
    RECEIPT_ITEM {
        bigint id PK
        bigint receipt_id FK
        bigint order_item_id FK
        int received_qty
        int normal_qty
        int defect_qty
        numeric actual_price
        varchar defect_reason
    }
    RECEIPT_INVOICE {
        bigint id PK
        bigint receipt_id FK
        varchar invoice_no
        date invoice_date
        numeric invoice_amount
        date payment_due_date
        varchar payment_status
    }
    BUDGET {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar fiscal_year
        varchar budget_code
        varchar budget_name
        numeric total_amount
        numeric committed_amount
        numeric spent_amount
        varchar status "ACTIVE|CLOSED"
    }
    BUDGET_ALLOCATION {
        bigint id PK
        bigint budget_id FK
        varchar allocation_code "DEPT|ITEM_TYPE|..."
        varchar allocation_target
        numeric allocated_amount
        numeric remaining_amount
    }
    BUDGET_TRANSACTION {
        bigint id PK
        bigint budget_id FK
        bigint allocation_id FK
        varchar txn_type "COMMIT|DISBURSE|REFUND|REALLOC|CARRYOVER"
        numeric amount
        bigint ref_order_id FK
        bigint ref_receipt_id FK
        text reason
        timestamptz txn_at
    }
    DONATION {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar donor_name_enc
        varchar donor_contact_enc
        date received_date
        varchar status "RECEIVED|REVIEWING|ACCEPTED|REJECTED|REGISTERED"
        text note
    }
    DONATION_ITEM {
        bigint id PK
        bigint donation_id FK
        varchar title
        varchar isbn
        int qty
        numeric estimated_value
        bigint resulting_copy_id FK
    }
    SERIAL_SUBSCRIPTION {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint vendor_id FK
        bigint bibliography_id FK
        varchar issn
        varchar frequency "DAILY|WEEKLY|MONTHLY|QUARTERLY|ANNUAL|IRREGULAR"
        date subscribe_from
        date subscribe_to
        numeric subscription_fee
        varchar status
    }
    SERIAL_ISSUE {
        bigint id PK
        bigint subscription_id FK
        varchar volume
        varchar issue_no
        date expected_date
        date received_date
        varchar status "EXPECTED|RECEIVED|MISSING|CLAIMED|BOUND"
        bigint resulting_copy_id FK
    }
```

### 5.1 ACQ 엔티티 목록 (16)

acq_request, acq_request_approval, vendor, purchase_order, purchase_order_item, purchase_order_approval, receipt, receipt_item, receipt_invoice, budget, budget_allocation, budget_transaction, donation, donation_item, serial_subscription, serial_issue.

---

## 6. CIR — 열람(Circulation) 도메인

```mermaid
erDiagram
    MEMBER ||--o{ LOAN : borrows
    COPY ||--o{ LOAN : lent_as
    LOAN ||--o{ LOAN_RENEWAL : renewed
    LOAN ||--o| RETURN : returned_as
    LOAN ||--o{ FINE : incurs
    LOAN ||--o{ LOST_DAMAGED_REPORT : reported

    MEMBER ||--o{ HOLD : reserves
    COPY ||--o{ HOLD : reserved_as
    BIBLIOGRAPHY ||--o{ HOLD : on_title
    HOLD ||--o{ HOLD_QUEUE : queued

    FINE ||--o{ FINE_PAYMENT : paid_by

    MEMBER ||--o{ MEMBER_BLOCK : blocked

    ILL_REQUEST }o--|| MEMBER : requested_by
    ILL_REQUEST }o--|| LIBRARY : source
    ILL_REQUEST }o--|| LIBRARY : destination

    SIP2_TRANSACTION ||--o| LOAN : results

    OPAC_SEARCH_LOG ||--o| MEMBER : by

    LOAN {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK "대출 발생 관"
        bigint member_id FK
        bigint copy_id FK
        timestamptz checkout_at
        date due_date
        timestamptz returned_at
        bigint return_library_id FK
        int renewal_count
        varchar status "ACTIVE|RETURNED|OVERDUE|LOST|CLAIMED_RETURNED"
        varchar checkout_method "COUNTER|SELF|MOBILE|SIP2"
        bigint operator_id FK
    }
    LOAN_RENEWAL {
        bigint id PK
        bigint loan_id FK
        date previous_due_date
        date new_due_date
        varchar renewal_method "OPAC|COUNTER|AUTO"
        bigint operator_id FK
        timestamptz renewed_at
    }
    RETURN {
        bigint id PK
        bigint loan_id FK
        bigint copy_id FK
        bigint return_library_id FK
        timestamptz returned_at
        varchar return_method "COUNTER|SELF|DROPBOX"
        varchar condition "NORMAL|MINOR|DAMAGE|LOST"
        bigint operator_id FK
    }
    HOLD {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint member_id FK
        bigint bibliography_id FK
        bigint copy_id FK "특정 권 지정 가능"
        bigint pickup_library_id FK
        int queue_position
        varchar status "WAITING|READY|FULFILLED|CANCELED|EXPIRED"
        timestamptz placed_at
        timestamptz ready_at
        timestamptz expires_at
    }
    HOLD_QUEUE {
        bigint id PK
        bigint bibliography_id FK
        bigint hold_id FK
        int position
        timestamptz queued_at
    }
    FINE {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint member_id FK
        bigint loan_id FK
        varchar fine_type "OVERDUE|LOST|DAMAGE|PROCESSING"
        numeric amount
        numeric paid_amount
        numeric waived_amount
        int overdue_days
        varchar status "PENDING|PARTIAL|PAID|WAIVED"
        timestamptz incurred_at
    }
    FINE_PAYMENT {
        bigint id PK
        bigint fine_id FK
        numeric amount
        varchar method "CASH|CARD|BANK|MOBILE|WAIVE"
        bigint operator_id FK
        varchar receipt_no
        timestamptz paid_at
    }
    LOST_DAMAGED_REPORT {
        bigint id PK
        bigint tenant_id FK
        bigint loan_id FK
        bigint copy_id FK
        bigint member_id FK
        varchar report_type "LOST|DAMAGED"
        varchar damage_severity "MINOR|MAJOR|UNUSABLE"
        text description
        varchar compensation_type "MONEY|SAME_ITEM|EQUIVALENT"
        numeric compensation_amount
        varchar status "REPORTED|REVIEWING|COMPENSATED|RESOLVED|REFUNDED"
        timestamptz reported_at
    }
    MEMBER_BLOCK {
        bigint id PK
        bigint member_id FK
        varchar block_type "OVERDUE|FINE_UNPAID|LOST|MANUAL"
        text reason
        date block_from
        date block_to
        varchar status "ACTIVE|RELEASED"
        bigint released_by FK
    }
    ILL_REQUEST {
        bigint id PK
        bigint tenant_id FK
        bigint source_library_id FK "소장관"
        bigint dest_library_id FK "신청관"
        bigint member_id FK
        bigint bibliography_id FK
        bigint copy_id FK
        varchar request_type "INTRA_TENANT|EXTERNAL"
        varchar external_partner "KERIS|KOLIS|..."
        varchar status "REQUESTED|APPROVED|SHIPPED|RECEIVED|LENT|RETURNED|CANCELED"
        timestamptz requested_at
        date due_date
    }
    SIP2_TRANSACTION {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar device_id
        varchar sip2_command "09|11|29|..."
        jsonb request_payload
        jsonb response_payload
        varchar result_code
        int duration_ms
        timestamptz txn_at
    }
    DEVICE_SELFCHECK {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar device_code UK
        varchar device_type "SELFCHECK|SELFRETURN|SMART_DROP"
        varchar status "ONLINE|OFFLINE|ERROR|MAINT"
        timestamptz last_heartbeat_at
    }
    OPAC_SEARCH_LOG {
        bigint id PK
        bigint tenant_id FK
        bigint member_id FK
        varchar query
        jsonb filters
        int result_count
        timestamptz searched_at
    }
    OPAC_FAVORITE {
        bigint id PK
        bigint member_id FK
        bigint bibliography_id FK
        varchar tag
        timestamptz added_at
    }
    EBOOK_LICENSE {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar platform
        varchar license_type
        int concurrent_users
        date valid_from
        date valid_to
    }
```

### 6.1 CIR 엔티티 목록 (16)

loan, loan_renewal, return, hold, hold_queue, fine, fine_payment, lost_damaged_report, member_block, ill_request, sip2_transaction, device_selfcheck, opac_search_log, opac_favorite, ebook_license, (counter_session Y2).

---

## 7. ACS — 출입관리(Access Control) 도메인

```mermaid
erDiagram
    LIBRARY ||--o{ GATE : has
    GATE ||--o{ ACCESS_EVENT : produces
    GATE ||--o{ EAS_ALARM : detects
    GATE ||--o{ GATE_DEVICE_STATUS : status_of

    MEMBER ||--o{ ACCESS_EVENT : performs
    MEMBER ||--o{ TEMP_PASS : issued_to
    MEMBER ||--o{ SECURITY_EVENT : involved_in

    ACCESS_POLICY ||--o{ ACCESS_EVENT : evaluated_by
    EAS_ALARM ||--o{ SECURITY_EVENT : escalates_to

    GATE {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar gate_code UK
        varchar gate_name
        varchar gate_type "ENTRY|EXIT|BIDIR|EAS_ONLY"
        varchar location_zone
        boolean eas_enabled
        varchar device_model
        varchar protocol "HTTP|SERIAL|TCP"
    }
    ACCESS_EVENT {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint gate_id FK
        bigint member_id FK
        varchar member_card_no
        varchar auth_method "BARCODE|QR|IC|NFC|BIOMETRIC|TEMP"
        varchar direction "IN|OUT"
        varchar result "ALLOW|DENY"
        varchar deny_reason
        timestamptz event_at
    }
    EAS_ALARM {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint gate_id FK
        bigint copy_id FK "식별된 자료"
        varchar rfid_uid
        bigint member_id FK "추정"
        varchar alarm_type "UNRETURNED|TAG_TAMPERED|UNKNOWN"
        varchar status "RAISED|REVIEWING|FALSE_ALARM|RESOLVED|ESCALATED"
        timestamptz alarmed_at
    }
    ACCESS_POLICY {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar member_type
        jsonb time_window "weekday,hour ranges"
        jsonb zone_allow
        boolean block_on_overdue
        boolean block_on_suspension
        int priority
    }
    TEMP_PASS {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar visitor_name_enc
        varchar visitor_contact_enc
        varchar visit_purpose
        varchar pass_code UK
        timestamptz valid_from
        timestamptz valid_to
        bigint issued_by FK
        varchar status "ISSUED|USED|EXPIRED|REVOKED"
    }
    SECURITY_EVENT {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar event_type "THEFT_ALARM|UNAUTH_ENTRY|DEVICE_FAULT|TAMPER"
        bigint ref_alarm_id FK
        bigint ref_event_id FK
        bigint member_id FK
        varchar severity "INFO|WARN|CRITICAL"
        varchar status "OPEN|HANDLING|CLOSED"
        text resolution
        timestamptz occurred_at
        timestamptz closed_at
    }
    GATE_DEVICE_STATUS {
        bigint id PK
        bigint gate_id FK
        varchar status "ONLINE|OFFLINE|ERROR"
        int latency_ms
        text error_msg
        timestamptz reported_at
    }
    OCCUPANCY_SNAPSHOT {
        bigint id PK
        bigint library_id FK
        int current_count
        jsonb zone_counts
        timestamptz snapshot_at
    }
    NEIS_SYNC_LOG {
        bigint id PK
        bigint tenant_id FK
        varchar sync_type
        int record_count
        timestamptz synced_at
    }
```

### 7.1 ACS 엔티티 목록 (9)

gate, access_event, eas_alarm, access_policy, temp_pass, security_event, gate_device_status, occupancy_snapshot, neis_sync_log.

---

## 8. FAC — 시설(Facility) 도메인

```mermaid
erDiagram
    LIBRARY ||--o{ SEAT_ZONE : has
    SEAT_ZONE ||--o{ SEAT : contains
    LIBRARY ||--o{ ROOM : has

    SEAT ||--o{ SEAT_RESERVATION : reserved
    MEMBER ||--o{ SEAT_RESERVATION : reserves
    SEAT_RESERVATION ||--o{ SEAT_EVENT : has

    ROOM ||--o{ ROOM_RESERVATION : reserved
    MEMBER ||--o{ ROOM_RESERVATION : reserves
    ROOM_RESERVATION ||--o{ ROOM_APPROVAL : approved_by

    SEAT ||--o{ FACILITY_ISSUE : reported
    ROOM ||--o{ FACILITY_ISSUE : reported

    FACILITY_POLICY ||--o{ SEAT_RESERVATION : evaluated
    FACILITY_POLICY ||--o{ ROOM_RESERVATION : evaluated

    SEAT_ZONE {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar zone_code
        varchar zone_name
        varchar zone_type "READING|GROUP|SILENT|PRIORITY"
        int capacity
    }
    SEAT {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint zone_id FK
        varchar seat_no
        jsonb features "outlet|monitor|lighting"
        boolean is_priority "장애인/우선좌석"
        varchar status "AVAILABLE|RESERVED|OCCUPIED|MAINT|DISABLED"
    }
    SEAT_RESERVATION {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint member_id FK
        bigint seat_id FK
        timestamptz reserved_from
        timestamptz reserved_to
        timestamptz checked_in_at
        timestamptz checked_out_at
        int extension_count
        varchar status "RESERVED|CHECKED_IN|EXTENDED|RELEASED|EXPIRED|NO_SHOW"
        varchar release_reason
    }
    SEAT_EVENT {
        bigint id PK
        bigint reservation_id FK
        varchar event_type "RESERVE|CHECKIN|EXTEND|LEAVE|RETURN|RELEASE"
        timestamptz event_at
    }
    ROOM {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar room_code
        varchar room_name
        varchar room_type "MEETING|SEMINAR|STUDIO"
        int capacity
        jsonb amenities
        boolean requires_approval
        boolean is_paid
        numeric hourly_fee
    }
    ROOM_RESERVATION {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        bigint member_id FK
        bigint room_id FK
        timestamptz reserved_from
        timestamptz reserved_to
        text purpose
        int participant_count
        varchar status "REQUESTED|APPROVED|REJECTED|USED|CANCELED|NO_SHOW"
        boolean is_recurring
    }
    ROOM_APPROVAL {
        bigint id PK
        bigint reservation_id FK
        int step_no
        bigint approver_id FK
        varchar decision
        text comment
        timestamptz decided_at
    }
    FACILITY_ISSUE {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar target_type "SEAT|ROOM|ZONE|OTHER"
        bigint target_id
        bigint reporter_id FK
        text description
        jsonb attachments
        varchar severity
        varchar status "REPORTED|ASSIGNED|IN_PROGRESS|RESOLVED|CLOSED"
        bigint assignee_id FK
        timestamptz reported_at
        timestamptz resolved_at
    }
    FACILITY_CHECKUP {
        bigint id PK
        bigint library_id FK
        varchar target_type
        bigint target_id
        date checkup_date
        text checklist_result
        bigint operator_id FK
    }
    FACILITY_CLOSE_SCHEDULE {
        bigint id PK
        bigint library_id FK
        varchar target_type
        bigint target_id
        date close_from
        date close_to
        text reason
    }
    LOST_FOUND {
        bigint id PK
        bigint library_id FK
        text item_description
        date found_date
        bigint reporter_id FK
        bigint claimed_by FK
        date claimed_date
        varchar status
    }
    FACILITY_POLICY {
        bigint id PK
        bigint tenant_id FK
        bigint library_id FK
        varchar target_type
        varchar member_type
        jsonb rules "max_hours,advance_days,..."
        date effective_from
        date effective_to
    }
```

### 8.1 FAC 엔티티 목록 (11)

seat_zone, seat, seat_reservation, seat_event, room, room_reservation, room_approval, facility_issue, facility_checkup, facility_close_schedule, lost_found, facility_policy.

---

## 9. 도메인 간 외래키 관계 (Cross-Domain FK)

```mermaid
flowchart TB
    subgraph CMN
        T[TENANT]
        L[LIBRARY]
        M[MEMBER]
        P[POLICY]
        LOC[LOCATION/SHELF]
    end

    subgraph CAT
        BIB[BIBLIOGRAPHY]
        AUTH[AUTHORITY]
    end

    subgraph COL
        HLD[HOLDING]
        CPY[COPY]
    end

    subgraph ACQ
        REQ[ACQ_REQUEST]
        PO[PURCHASE_ORDER]
        POITM[PO_ITEM]
        RCP[RECEIPT]
        BGT[BUDGET]
        SER[SERIAL_SUBSCRIPTION]
        SISS[SERIAL_ISSUE]
    end

    subgraph CIR
        LN[LOAN]
        HD[HOLD]
        FN[FINE]
        ILL[ILL_REQUEST]
    end

    subgraph ACS
        AE[ACCESS_EVENT]
        EAS[EAS_ALARM]
    end

    subgraph FAC
        STR[SEAT_RESERVATION]
        RMR[ROOM_RESERVATION]
    end

    BIB --> HLD
    HLD --> CPY
    LOC --> CPY
    REQ --> POITM
    PO --> POITM
    POITM --> RCP
    RCP --> CPY
    BGT --> POITM
    SER --> SISS
    SISS --> CPY
    M --> LN
    CPY --> LN
    M --> HD
    BIB --> HD
    CPY --> HD
    LN --> FN
    LN --> ILL
    CPY --> EAS
    M --> AE
    M --> STR
    M --> RMR
    L -.tenant 전체에.-> CMN
    L -.library_id 분기.-> COL
    L -.library_id 분기.-> CIR
    L -.library_id 분기.-> ACS
    L -.library_id 분기.-> FAC
```

### 9.1 핵심 도메인 간 연결 정리

| 출발 | 도착 | 의미 |
|---|---|---|
| `tlp_cat_bibliography.id` | `tlp_col_holding.bibliography_id` | 서지 → 소장 |
| `tlp_col_holding.id` | `tlp_col_copy.holding_id` | 소장 → 개별자료 |
| `tlp_col_copy.id` | `tlp_cir_loan.copy_id` | 자료 → 대출 |
| `tlp_cir_loan.id` | `tlp_cir_fine.loan_id` | 대출 → 연체료 |
| `tlp_cir_loan.id` | `tlp_cir_lost_damaged_report.loan_id` | 대출 → 분실/훼손 |
| `tlp_acq_purchase_order_item.id` | `tlp_acq_receipt_item.order_item_id` | 발주 → 검수 |
| `tlp_acq_receipt_item.id` → 채번 → | `tlp_col_copy` | 검수 → 등록 |
| `tlp_acq_serial_issue.id` | `tlp_col_copy.id` | 호 → 자료(권차) |
| `tlp_col_copy.id` | `tlp_acs_eas_alarm.copy_id` | 자료 → EAS 경보 |
| `tlp_cmn_member.id` | `tlp_cir_loan.member_id`, `tlp_acs_access_event.member_id`, `tlp_fac_*_reservation.member_id` | 회원 → 모든 트랜잭션 |
| `tlp_cmn_library.id` | `tlp_col_copy.library_id`, `tlp_cir_loan.library_id`, ... | 다관 분기 |

---

## 10. 다관(Library) 분기 표현 — 핵심 격리 규칙

| 테이블 | tenant_id | library_id | 비고 |
|---|---|---|---|
| `tlp_cmn_member` | ✅ | NULL(테넌트 회원) | 다관 공유 회원 |
| `tlp_cat_bibliography` | ✅ | NULL | 서지는 테넌트 공유 (권장) |
| `tlp_col_holding` | ✅ | ✅ | 관별 소장 |
| `tlp_col_copy` | ✅ | ✅ | 관별 등록번호 |
| `tlp_acq_purchase_order` | ✅ | ✅ | 관별 발주 |
| `tlp_cir_loan` | ✅ | ✅ | 대출 발생 관 |
| `tlp_acs_access_event` | ✅ | ✅ | 관별 게이트 |
| `tlp_fac_seat_reservation` | ✅ | ✅ | 관별 좌석 |

- 다관 통합대출(`is_integrated_loan = true`)인 테넌트는 회원이 모든 관의 자료를 대출 가능.
- 단관 운영 테넌트는 sentinel `library_id = <기본관 id>` 1개 강제.

---

## 11. 카디널리티·필수/옵션 정리 (요약)

| 관계 | 카디널리티 | 옵션 |
|---|---|---|
| Tenant → Library | 1:N | 1 이상 필수 |
| Library → Library (parent) | 0..1:N | 본관-분관 |
| Bibliography → Holding | 1:N | 0 가능 (서지만 등록한 미입수) |
| Holding → Copy | 1:N | 1 이상 권장 |
| Member → Loan | 1:N | 0 가능 |
| Copy → Loan | 1:N (시점별 1대출 활성) | 동시 ACTIVE 1건 제약 |
| Loan → Fine | 1:N | 0 가능 |
| Hold → Loan (이행) | 0..1:0..1 | 예약 → 대출 |
| AcqRequest → PO_Item | 0..1:1 | OPAC 신청 미경유 발주 가능 |
| Serial_Subscription → Serial_Issue | 1:N | 예측·실입수 |

---

## 12. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v0.1 | 2026-05-11 | DBA Agent | 100개 엔티티 식별, 7개 도메인 ERD 작성, 도메인 간 FK 명시. |
