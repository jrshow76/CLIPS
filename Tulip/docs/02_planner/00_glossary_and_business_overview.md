# 용어집 & 업무 개요 (Glossary & Business Overview)

| 항목 | 내용 |
|---|---|
| 문서명 | 용어집 & 업무 개요 |
| 문서 ID | PLN-00 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | Planner Agent |
| 검토자 | PM, DevLead, DBA, Designer |
| 상태 | 초안 |

---

## 1. 문서 목적

본 문서는 Tulip+ 도서관통합관리시스템의 **업무 도메인 용어를 표준화**하고, 도서관 유형별 운영 차이와 멀티테넌트(다관) 운영 개념을 정의하여 이후 모든 산출물(요구사항·설계·구현)의 기준 용어를 통일하는 데 목적이 있다.

- 본 문서의 용어는 화면/API/DB 객체명·로그·문서 전반에서 동일하게 사용한다.
- 표준 출처: KORMARC 통합서지용(국립중앙도서관), KOLIS-NET, KERIS·DLS 권고안.

---

## 2. 핵심 용어 정의

### 2.1 자료·서지 관련

| 용어 | 영문 / 약어 | 정의 |
|---|---|---|
| 서지 | Bibliographic Record | 자료의 식별·기술 정보(저자·서명·발행처 등)를 담는 단위 레코드. KORMARC 포맷으로 관리. |
| 저작 | Work (FRBR) | 지적·예술적 창작의 추상적 단위. 예: 셰익스피어의 "햄릿"이라는 작품 자체. |
| 표현형 | Expression (FRBR) | 저작의 언어·형식적 실현. 예: "햄릿" 한국어 번역본. |
| 구현형 | Manifestation (FRBR) | 표현형의 물리적 제작. 예: A출판사 2024년판 "햄릿". |
| 개별자료 | Item (FRBR) | 도서관이 실제 소장한 한 권. 등록번호로 식별. |
| 소장 | Holding | 특정 도서관(관)이 어떤 서지를 몇 권·어디에 보유하는지의 정보. |
| 등록번호 | Accession No. | 개별자료에 부여되는 도서관 내 고유 번호. 일반적으로 다관 분기 채번. |
| 청구기호 | Call Number | 분류기호 + 도서기호 + 권차/복본 등으로 구성된 서가 배치 식별자. |
| KORMARC | KORean MAchine Readable Cataloging | 국립중앙도서관 제정 한국형 MARC 포맷. |
| MARC21 | MAchine Readable Cataloging 21 | LOC 제정 국제 MARC 포맷. |
| ISBD | International Standard Bibliographic Description | 국제표준서지기술법. |
| 권위레코드 | Authority Record | 표목(저자명·주제명·통일서명)의 표준형을 관리하는 레코드. |
| 분류 | Classification | KDC(한국십진분류), DDC(듀이), LC(미국의회), UDC 등 주제 분류 체계. |
| 주제어 | Subject Heading | LCSH·NDLSH·국립중앙도서관주제명표목표 등. |
| 단행본 | Monograph | 1책 또는 한정된 책 수로 완결된 자료. |
| 연속간행물 | Serial | 잡지·신문·연보 등 지속 발행 자료. |
| 비도서자료 | Non-book material | DVD, CD, 지도, 악보, 마이크로폼 등. |
| 전자자원 | Electronic Resource | 전자책·전자저널·DB·웹자료. |

### 2.2 이용자·회원 관련

| 용어 | 영문 / 약어 | 정의 |
|---|---|---|
| 이용자 | Patron / User | 도서관 서비스를 이용하는 모든 사람. |
| 회원 | Member | 도서관에 등록되어 대출·예약 등 서비스를 받을 수 있는 이용자. |
| 정회원 | Regular Member | 본인 인증 완료, 모든 서비스 이용 가능. |
| 준회원 | Associate Member | 일부 서비스(검색·열람) 제한적 이용. |
| 회원증 | Library Card | 회원 식별 매체(IC카드·QR·바코드·모바일). |
| 통합회원증 | Unified Card | 다관 시스템에서 공유되는 단일 회원증. |
| 이용자 유형 | Patron Type | 학생·교직원·일반·외부·단체 등 정책 차등을 위한 분류. |
| SSO | Single Sign-On | 외부 인증(학교 SSO·LDAP·교육행정정보시스템) 연계. |

### 2.3 열람·대출 관련

| 용어 | 영문 / 약어 | 정의 |
|---|---|---|
| 대출 | Checkout / Loan | 자료를 회원에게 일정 기간 제공하는 행위. |
| 반납 | Return / Check-in | 대출자료의 회수. |
| 연장 | Renewal | 대출기간을 추가 연장. |
| 예약 | Reservation / Hold | 대출 중 자료에 대한 우선 대출 요청. |
| 예약 우선순위 | Hold Queue | 예약자 순번. |
| 연체 | Overdue | 반납예정일 초과. |
| 연체료 | Overdue Fine | 연체에 따른 패널티(금액 또는 이용제한 일수). |
| 이용제한 | Patron Block | 연체·분실 등 사유로 서비스 이용을 정지. |
| 관간대차 | ILL (Inter-Library Loan) | 다관 간 자료 이동 대출. |
| OPAC | Online Public Access Catalog | 이용자용 온라인 검색·조회 시스템. |
| 자가대출 | Self-checkout | RFID/바코드 자가대출기 이용 대출. |
| SIP2 | Standard Interchange Protocol v2 | 도서관-자가대출기 통신 프로토콜. |
| NCIP | NISO Circulation Interchange Protocol | 도서관 시스템 간 대출 정보 교환 표준. |
| 분실/훼손 | Lost / Damaged | 자료 분실·훼손 처리 상태. |
| 변상 | Compensation | 분실·훼손에 따른 금전 또는 동종 자료 변상. |

### 2.4 수서 관련

| 용어 | 영문 / 약어 | 정의 |
|---|---|---|
| 수서 | Acquisition | 자료의 선정·구입·기증·교환·구독을 통한 입수. |
| 희망도서 | Patron Request / Suggestion | 이용자가 신청한 구입 희망 자료. |
| 선정 | Selection | 구입할 자료를 결정하는 행위. |
| 발주 | Order | 납품처에 자료 구입을 의뢰. |
| 검수 | Inspection / Receipt | 납품된 자료의 수량·상태·가격 확인. |
| 납품처 | Vendor / Supplier | 자료를 공급하는 서점·출판사. |
| 예산 | Budget | 자료 구입을 위한 회계 예산. |
| 집행 | Disbursement | 예산을 발주·결제에 사용. |
| 이월 | Carry-over | 미집행 예산을 차기로 이전. |
| 기증 | Donation | 무상으로 받은 자료. |
| 교환 | Exchange | 다른 기관과 자료를 상호 교환. |
| 연속간행물 구독 | Subscription | 정기간행물의 정기 구입 계약. |
| ISBN | International Standard Book Number | 도서 국제표준식별번호. |

### 2.5 장서관리 관련

| 용어 | 영문 / 약어 | 정의 |
|---|---|---|
| 장서 | Collection | 도서관이 소장한 자료 전체. |
| 장서점검 | Inventory | 등록된 자료가 실제 서가에 있는지 확인하는 정기 점검. |
| 분실(미확인) | Missing | 점검 시 발견되지 않은 자료. |
| 오배가 | Misshelved | 잘못된 위치에 배가된 자료. |
| 이관 | Transfer | 자료를 한 관·서가에서 다른 관·서가로 이동. |
| 재배가 | Reshelving | 동일 도서관 내 위치 변경. |
| 제적 | Withdrawal | 장서에서 영구히 제외(파기·분실확정·기증반출 등). |
| 폐기 | Discard | 제적된 자료의 물리적 처분. |
| 보존서가 | Closed Stack | 폐가식 보존 자료 서가. |
| 귀중자료 | Rare Material | 별도 보존·열람 통제가 필요한 자료. |

### 2.6 출입·시설 관련

| 용어 | 영문 / 약어 | 정의 |
|---|---|---|
| 출입게이트 | Gate | 회원 인증으로 출입을 통제하는 장비. |
| EAS | Electronic Article Surveillance | 도난방지 시스템. |
| 도난경보 | Theft Alarm | EAS에서 검출된 미반납 자료 통과 경보. |
| 재실현황 | Occupancy | 현재 도서관 내 체류 인원 현황. |
| 임시증 | Temporary Card | 외부방문자에게 발급되는 일회성 출입증. |
| 좌석예약 | Seat Reservation | 일반 열람석·캐럴 좌석 사전·즉시 예약. |
| 캐럴 | Carrel | 개인 학습 부스(독립 칸막이 좌석). |
| 회의실/세미나실 | Meeting/Seminar Room | 집단 이용 시설. |
| 휴관일 | Closed Day | 도서관 운영 중단일. |

### 2.7 시스템·플랫폼 관련

| 용어 | 영문 / 약어 | 정의 |
|---|---|---|
| 테넌트 | Tenant | SaaS에서 격리된 고객 단위. Tulip+에서는 "도서관 조직" 단위. |
| 관 | Library Branch | 한 테넌트가 운영하는 개별 분관·캠퍼스도서관. |
| 다관 통합 | Multi-branch | 한 테넌트가 여러 관을 함께 운영. |
| RBAC | Role-Based Access Control | 역할 기반 권한 관리. |
| ABAC | Attribute-Based Access Control | 속성 기반 권한 관리. |
| SaaS | Software as a Service | 클라우드 서비스형 SW 제공 모델. |

---

## 3. 도서관 유형별 업무 특수성 비교

### 3.1 운영 환경 비교표

| 구분 | 공공도서관 | 대학·전문도서관 | 학교도서관 |
|---|---|---|---|
| **이용자 유형** | 일반시민·어린이·청소년·단체 (다양) | 학생·대학원생·교직원·외부이용자 | 재학생·교사·교직원 |
| **회원증** | 통합도서관증·시민카드 연계 | 학생증·교직원증 통합 | 학생증·NEIS 연계 |
| **인증 표준** | 행정안전부 mIDR / 자체 | 학교 SSO / LDAP / KERIS | NEIS / 교육행정정보시스템 |
| **공동목록** | KOLIS-NET (국립중앙도서관) | KERIS-RISS / 학술공동목록 | DLS (학교도서관 DLS) |
| **분류** | KDC 주 사용 | KDC/DDC/LC 혼용 | KDC |
| **대출권수·기간** | 일반 5~7권 / 14일 | 학부 10권/21일, 대학원 20~30권/30~60일 | 학생 3~5권/7~14일 |
| **연체정책** | 연체일수만큼 이용정지 다수 | 연체료·이용정지 혼용 | 연체일수 이용정지 |
| **수서 특징** | 희망도서·기증 비중 高 | 학과별 예산 배분·전자자원 비중 高 | 학년·교과 맞춤 선정 |
| **장서규모** | 수만~수백만 권 | 수십만~수백만 권 | 수천~수만 권 |
| **OPAC 사용자** | 일반시민(모바일 비중 高) | 학생(원격접속·DRM 이용 多) | 학생·교사(NEIS 통합) |
| **시설예약** | 동아리실·세미나실 多 | 그룹스터디·캐럴 多 | 거의 없음(통합 열람실) |
| **출입통제** | 자유출입 多, 일부 게이트 | 게이트·EAS 일반화 | 출입체크(NEIS 연계) |
| **개인정보 민감도** | 매우 높음 (시민 정보) | 높음 (학적정보) | 매우 높음 (미성년자) |
| **다관 운영** | 시군구 통합관 多 | 본·분관 多 | 단일관 多 |

### 3.2 도메인별 적용 차이 요약

| 도메인 | 공공 핵심 기능 | 대학 핵심 기능 | 학교 핵심 기능 |
|---|---|---|---|
| 수서 | 희망도서 비중, 기증 처리 多 | 학과별 예산, 전자자원 구독 | 교과연계 추천도서 |
| 목록 | KOLIS-NET 활용 多 | KERIS 학술공동목록 | DLS 공동목록 |
| 열람 | 통합대출(다관) | 관간대차·전자자원 인증 | 학기제·방학 별 정책 |
| 장서관리 | 폐기·기증 비중 高 | 보존서가·학위논문 | 교과서·교구 별도 관리 |
| 출입관리 | 자유 출입·일부 게이트 | 게이트 필수·EAS 일반 | NEIS 연동 |
| 시설관리 | 동아리·세미나실 | 그룹스터디·캐럴 多 | 거의 없음 |

---

## 4. 멀티테넌트(다관) 운영 개념

### 4.1 계층 구조

```
[플랫폼 (Tulip+)]
  └─ [테넌트(Tenant) = 도서관 조직]
        ├─ [관(Branch) 1] — 본관
        ├─ [관(Branch) 2] — 분관 A
        └─ [관(Branch) 3] — 분관 B
              ├─ [서가/장소(Location)]
              ├─ [회원(Member) — 테넌트 또는 관 단위]
              └─ [자료(Holding) — 관 단위 소장]
```

### 4.2 데이터 격리 원칙

| 격리 수준 | 적용 영역 | 비고 |
|---|---|---|
| **물리적 격리(Schema)** | (옵션) 대형 기관 전용 인스턴스 | Y2 이상 |
| **논리적 격리(Row + tenant_id)** | 기본 격리 방식 | 전 영역 적용 |
| **공유(Shared)** | 코드테이블·국가표준 분류표 | 마스터 데이터만 |

### 4.3 정책 분리 원칙

| 정책 영역 | 정책 적용 단위 | 예시 |
|---|---|---|
| 회원·인증 | 테넌트 | 회원유형, 인증방식, SSO 연결 |
| 대출·예약 정책 | 관(Branch) | 관마다 권수·기간 다를 수 있음 |
| 자료 채번 | 관(Branch) | 등록번호 채번 규칙 분기 |
| OPAC 노출 | 관 또는 통합 | 통합검색 vs 관별검색 선택 |
| 출입·시설 | 관(Branch) | 관마다 게이트·시설 별도 |
| 통계·리포트 | 테넌트/관 | 두 단위 모두 집계 가능 |
| 예산·회계 | 테넌트 | 통합 회계, 관별 배분 가능 |

### 4.4 통합/분리 운영 패턴

| 운영 패턴 | 설명 | 대상 |
|---|---|---|
| **단관 운영** | 테넌트=1관, 단일 정책 | 학교·소규모 공공·전문 |
| **다관 통합** | 다관, 통합 OPAC·통합 대출·통합 회원 | 시군구 통합 공공도서관 |
| **다관 분리** | 다관, 관별 정책 독립, 관간대차만 연계 | 대학(본·분관 분리 운영) |
| **혼합형** | 일부 정책 통합, 일부 분리 | 시도교육청 학교군 |

---

## 5. 표준·외부 시스템 개요

| 표준/시스템 | 주관기관 | 용도 | Tulip+ 연계 방식 |
|---|---|---|---|
| **KORMARC** | 국립중앙도서관 | 한국형 서지포맷(필수) | 입출력 표준 |
| **MARC21** | LOC | 국제 서지포맷 | KORMARC ↔ 변환 |
| **Z39.50** | NISO | 서지 검색·복사목록 표준 | 외부 서지 검색 |
| **KOLIS-NET** | 국립중앙도서관 | 공동목록·공공도서관 통합 | 업로드/다운로드 |
| **KERIS-RISS** | 한국교육학술정보원 | 학술자원 공동목록 | 대학용 연계 |
| **DLS** | KERIS | 학교도서관 통합지원시스템 | 학교용 연계 |
| **SIP2** | 3M·NCIP 그룹 | 자가대출기 통신 | RFID 키오스크 |
| **NCIP** | NISO | 시스템 간 대출 정보 교환 | 관간대차·자가대출 |
| **EAS** | 다수 벤더 | 도난방지 시스템 | 게이트 이벤트 수신 |
| **NEIS** | 교육부 | 학생·교사 학적정보 | 학교용 회원 동기화 |

---

## 6. 약어 사전

| 약어 | 풀이 |
|---|---|
| ACQ | Acquisition (수서) |
| CAT | Cataloging (목록) |
| CIR | Circulation (열람·대출) |
| COL | Collection (장서관리) |
| ACS | Access Control (출입관리) |
| FAC | Facility (시설관리) |
| CMN | Common (공통) |
| OPAC | Online Public Access Catalog |
| ILL | Inter-Library Loan |
| RFID | Radio Frequency Identification |
| EAS | Electronic Article Surveillance |

---

## 7. 후속 문서

| 후속 산출물 | 참조 |
|---|---|
| 공통 요구사항 | `01_common_requirements.md` |
| 수서 요구사항 | `02_acquisition_requirements.md` |
| 목록 요구사항 | `03_cataloging_requirements.md` |
| 열람 요구사항 | `04_circulation_requirements.md` |
| 장서관리 요구사항 | `05_collection_requirements.md` |
| 출입관리 요구사항 | `06_access_control_requirements.md` |
| 시설관리 요구사항 | `07_facility_requirements.md` |
| 화면 흐름·IA | `08_screen_flow_and_ia.md` |
