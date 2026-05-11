# Tulip+ — 도서관통합관리시스템

## 프로젝트 개요

Tulip+ 는 학교·대학·전문·공공(단일/다관) 도서관 전 유형을 단일 플랫폼에서 지원하는 **SaaS형 통합 도서관관리솔루션**이다.

## 핵심 스코프

| 구분 | 내용 |
|---|---|
| **타겟 도서관** | 학교 / 대학·전문 / 공공(단일관·다관 통합) |
| **업무 도메인** | 수서 · 목록 · 열람 · 장서관리 · 출입관리 · 시설관리 + 확장 |
| **서지 표준** | KORMARC (필수), MARC21 / Z39.50, KOLIS-NET, DLS·KERIS |
| **하드웨어 연동** | RFID 자가대출반납기(SIP2/NCIP), 출입게이트·도난방지(EAS), 바코드, SW-only |
| **아키텍처** | Spring Boot MSA + MyBatis / Next.js / PostgreSQL |
| **인증** | OAuth2 / JWT (멀티테넌트) |
| **인프라** | 클라우드 |
| **마이그레이션** | 신규 구축 (마이그레이션 없음) |

## 개발 로드맵

```
Phase 0  기획·설계  ← 현재
Phase 1  공통 기반 (인증·회원·코드·공통컴포넌트·API Gateway)
Phase 2  목록·장서  (KORMARC, KOLIS-NET 연동)
Phase 3  수서       (선정·발주·검수·예산)
Phase 4  열람       (대출·반납·예약·연체·OPAC)
Phase 5  출입·시설  (게이트·좌석·시설예약 + RFID/SIP2)
Phase 6  통계·확장  (통계·리포트·전자자료)
```

## 산출물 디렉토리

| 경로 | 담당 | 산출물 |
|---|---|---|
| `docs/00_overview/` | 공통 | 프로젝트 개요·용어집·표준 가이드 |
| `docs/01_pm/` | PM | 프로젝트 헌장·WBS·마일스톤·리스크 |
| `docs/02_planner/` | Planner | 업무 요구사항·기능명세·화면흐름 |
| `docs/03_designer/` | Designer | IA·디자인시스템·퍼블리싱 |
| `docs/04_dev_lead/` | DevLead | 아키텍처·API 표준·코드 규약 |
| `docs/05_backend/` | Backend | API 명세·도메인 모델 |
| `docs/06_frontend/` | Frontend | 컴포넌트 구조·상태관리 |
| `docs/09_qa/` | QA | 테스트 시나리오·결함 관리 |
| `docs/10_dba/` | DBA | ERD·인덱스·튜닝 가이드 |

## 기술 스택

- **Backend**: Java 17+, Spring Boot 3.x, Spring Cloud Gateway, MyBatis
- **Frontend**: Next.js (App Router), TypeScript, TanStack Query
- **Database**: PostgreSQL 15+
- **Infra**: Docker, Docker Compose, GitHub Actions, Kubernetes (예정)
- **표준 프로토콜**: SIP2 / NCIP (RFID 연동), Z39.50 (외부 서지 검색)
