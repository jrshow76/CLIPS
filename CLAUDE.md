# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 언어 규칙

모든 대화와 응답은 반드시 **한글**로 진행한다. 코드, 명령어, 고유명사를 제외한 모든 텍스트는 한글을 사용한다.

---

# 프로젝트 개발팀 구성 및 협업 구조

## 워크스페이스 개요

이 워크스페이스는 10개 역할로 구성된 멀티에이전트 개발팀 환경이다.
에이전트는 `.claude/agents/` 디렉토리에 정의되어 있으며, Claude Code의 서브에이전트 기능으로 호출된다.
각 에이전트는 역할에 특화된 행동 원칙과 협업 패턴을 따른다.

## 에이전트 목록 및 호출 기준

| 에이전트 | 파일 | 호출 시점 |
|---|---|---|
| **PM** | `01_pm.md` | 일정·범위·리스크 관리, 배포 승인, 장애 에스컬레이션 |
| **Planner** | `02_planner.md` | 요구사항 분석, 기능 정의, 화면 흐름 설계, API 요구사항 정의 |
| **Designer** | `03_designer.md` | 화면 설계, 디자인 시스템 구성, 반응형 UI, HTML/CSS 퍼블리싱 |
| **DevLead** | `04_dev_lead.md` | 기술 아키텍처 설계, API 구조 수립, 코드 리뷰, 개발 표준 관리, 장애 대응 기술 총괄 |
| **BackendSenior** | `05_backend_senior.md` | 복잡한 API, 대량 데이터 처리, 외부 시스템 연동, Batch 처리, 성능 최적화 |
| **BackendDev** | `06_backend_dev.md` | 일반 REST API 개발, CRUD 구현, 기능 유지보수, 단순 Batch 개발 |
| **FrontendSenior** | `07_frontend_senior.md` | 공통 컴포넌트 개발, 상태관리 구조 설계, 대시보드·차트·에디터 등 복잡한 UI, 성능 최적화 |
| **FrontendDev** | `08_frontend_dev.md` | 입력 폼, 리스트·상세 화면, API 연동, UI 유지보수 및 버그 수정 |
| **QA** | `09_qa.md` | 테스트 시나리오 설계, 기능 테스트(수동/자동화), 버그 등록·추적, 배포 전 품질 최종 검증 |
| **DBA** | `10_dba.md` | SQL 튜닝, 실행계획 분석, 인덱스 설계, Lock/트랜잭션 병목 분석, HA 구성, DB 접근 권한 관리 |

## 협업 흐름

```
고객 요구사항
      ↓
  PM ←→ Planner
      ↓
  Designer ←→ Planner
      ↓
  DevLead
   ↙        ↘
BackendSenior  FrontendSenior
   ↓                ↓
BackendDev     FrontendDev
        ↘      ↙
          QA
          ↕
         DBA
```

### 요구사항 흐름
1. **PM → Planner**: 고객 요구사항 전달, 우선순위 확정
2. **Planner → DevLead**: API 요구사항 정의서, 기능 명세서 전달
3. **Planner → Designer**: 화면 정의서, 메뉴 구조도 전달
4. **DevLead → 개발자**: 업무 분배, 기술 가이드, 코드 리뷰

### 개발 흐름
1. **Designer → FrontendSenior**: HTML/CSS 퍼블리싱 결과물 전달
2. **FrontendSenior**: React 컴포넌트 구조 설계, 공통 모듈 개발
3. **BackendSenior**: 핵심 API 개발, DBA 협의로 쿼리 최적화
4. **BackendDev / FrontendDev**: 가이드라인에 따라 기능 구현

### 품질 관리 흐름
1. **QA**: 기능 명세서 기반 테스트 케이스 작성 및 수행
2. **QA → DevLead**: 버그 우선순위 협의
3. **QA → PM**: 배포 전 QA 완료 보고
4. **PM**: QA 완료 보고서 확인 후 배포 승인

## 역할 경계 (충돌 방지)

| 업무 | 주도 | 협의 |
|---|---|---|
| SQL 최적화 | DBA | BackendSenior (쿼리 제공) |
| 인덱스 설계 | DBA | DevLead (방향 협의) |
| DB 권한 부여 실행 | DBA | DevLead (요청) |
| 공통 인증 구조 | DevLead (설계) → BackendSenior (구현) | — |
| 컴포넌트 구조 설계 | FrontendSenior | DevLead (기준 제시) |
| HTML/CSS 퍼블리싱 | Designer | — |
| React 컴포넌트화 | FrontendDev | FrontendSenior (가이드) |
| 장애 대응 (DB 계층) | DBA | DevLead (애플리케이션 계층) |

## 기술 스택

- **Backend**: Java, Spring Boot, Spring Batch, MyBatis / JPA
- **Frontend**: React, Next.js, TypeScript, TanStack Query
- **Database**: PostgreSQL
- **Infra**: Docker, Docker Compose, GitHub Actions
- **API 테스트**: Postman, Newman
- **E2E 테스트**: Playwright 또는 Cypress
- **협업 도구**: Git (PR 기반), Jira, Notion

## 개발 원칙

- 모든 기능 구현은 PR 기반으로 진행하며 DevLead가 최종 리뷰한다.
- API 설계 규약(공통 요청/응답 포맷, 에러 코드)을 반드시 준수한다.
- 복잡한 쿼리 작성 전 DBA와 협의한다.
- 배포는 QA 완료 보고서 확인 후 PM이 승인한다.
- 복잡한 비즈니스 로직·쿼리는 BackendSenior, 일반 CRUD는 BackendDev가 담당한다.
- 디자이너가 제공한 HTML/CSS 구조를 FrontendDev가 최대한 유지하여 컴포넌트화한다.
