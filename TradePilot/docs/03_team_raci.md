# TradePilot RACI 매트릭스

| 항목 | 내용 |
|---|---|
| 기준일 | 2026-05-12 |
| 작성자 | PM |

---

## 1. RACI 정의

| 코드 | 의미 | 설명 |
|---|---|---|
| **R** | Responsible (실행) | 실제로 작업을 수행하는 담당자 |
| **A** | Accountable (최종 책임) | 결과에 대한 최종 책임자 (각 업무당 1명) |
| **C** | Consulted (협의) | 의사결정 전 의견을 구해야 하는 사람 |
| **I** | Informed (정보 공유) | 결과를 공유받는 사람 |

> 한 사람이 R과 A를 겸할 수 있음. 단 A는 업무당 단 1명.

---

## 2. 역할 약어

| 약어 | 역할 |
|---|---|
| PM | Project Manager |
| PL | Planner |
| DS | Designer |
| DL | DevLead |
| BS | BackendSenior |
| BD | BackendDev |
| FS | FrontendSenior |
| FD | FrontendDev |
| QA | QA |
| DBA | DBA |

---

## 3. 단계별 RACI 매트릭스

### 3.1 프로젝트 관리

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 프로젝트 헌장 작성 | **A/R** | C | I | C | I | I | I | I | I | I |
| WBS·일정 수립 | **A/R** | C | C | C | C | I | C | I | C | C |
| 주간 진행 보고 | **A/R** | I | I | C | I | I | I | I | I | I |
| 리스크 관리 | **A/R** | C | I | C | C | I | I | I | C | C |
| 범위 변경 결정 | **A** | R | C | C | I | I | I | I | I | I |
| 고객 커뮤니케이션 | **A/R** | C | I | I | I | I | I | I | I | I |

### 3.2 요구사항·기획

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 요구사항 수집 | A | **R** | C | C | I | I | I | I | I | I |
| 기능 명세서 작성 | A | **R** | C | C | C | I | I | I | C | I |
| 화면 흐름도 작성 | A | **R** | **R** | I | I | I | C | I | C | I |
| API 요구사항 정의 | I | **R/A** | I | C | C | I | C | I | C | I |
| 우선순위 결정 | **A** | **R** | I | C | I | I | I | I | I | I |

### 3.3 설계 (아키텍처·DB·디자인)

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 시스템 아키텍처 설계 | I | C | I | **A/R** | C | I | C | I | I | C |
| API 표준·공통 포맷 정의 | I | C | I | **A/R** | C | C | C | C | I | I |
| DB 스키마 설계 | I | C | I | C | C | I | I | I | I | **A/R** |
| 인덱스·파티셔닝 설계 | I | I | I | C | C | I | I | I | I | **A/R** |
| 시계열 테이블 설계 | I | I | I | C | C | I | I | I | I | **A/R** |
| 와이어프레임 작성 | I | C | **A/R** | I | I | I | C | I | I | I |
| 디자인 시스템 구성 | I | I | **A/R** | C | I | I | C | C | I | I |
| HTML/CSS 퍼블리싱 | I | I | **A/R** | I | I | I | C | C | I | I |

### 3.4 백엔드 개발

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 크레온 게이트웨이(Windows COM) | I | I | I | C | **A/R** | I | I | I | I | I |
| 시세 수집기·실시간 수신 | I | I | I | C | **A/R** | C | I | I | I | C |
| 기술적 지표 계산 모듈 | I | C | I | C | **A/R** | C | I | I | I | I |
| LSTM 학습·추론 파이프라인 | I | C | I | C | **A/R** | I | I | I | I | I |
| 추천 엔진 | I | C | I | C | **A/R** | C | I | I | I | C |
| 백테스팅 엔진 | I | C | I | C | **A/R** | I | I | I | C | C |
| 매매 엔진(시뮬레이션) | I | C | I | C | **A/R** | I | I | I | C | I |
| 매매 엔진(실거래·주문 라우터) | A | C | I | C | **R** | I | I | I | C | I |
| Risk Guard / Kill Switch | A | I | I | C | **R** | I | I | I | C | I |
| 일반 CRUD API (사용자·설정) | I | C | I | C | C | **A/R** | I | I | I | I |
| 알림 서비스(웹 푸시·이메일) | I | C | I | C | C | **A/R** | I | I | I | I |
| 거래 로그·감사 추적 | I | I | I | C | C | **A/R** | I | I | C | C |

### 3.5 프론트엔드 개발

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 공통 컴포넌트·상태관리 | I | I | C | C | I | I | **A/R** | C | I | I |
| 대시보드·수익률 화면 | I | C | C | I | I | I | **A/R** | C | C | I |
| 차트·지표 오버레이 화면 | I | C | C | I | I | I | **A/R** | C | C | I |
| 백테스팅 결과 화면 | I | C | C | I | I | I | **A/R** | C | C | I |
| 추천 종목 리스트 | I | C | C | I | I | I | C | **A/R** | C | I |
| 매매 내역·체결 화면 | I | C | C | I | I | I | C | **A/R** | C | I |
| 전략 설정·모드 토글(이중확인) | A | C | C | C | C | I | C | **R** | C | I |
| 알림 센터·설정 화면 | I | C | C | I | I | I | C | **A/R** | C | I |

### 3.6 데이터·DB 운영

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| SQL 튜닝·실행계획 분석 | I | I | I | C | C | I | I | I | I | **A/R** |
| 인덱스 설계·적용 | I | I | I | C | C | I | I | I | I | **A/R** |
| DB 접근 권한 관리 | I | I | I | C | I | I | I | I | I | **A/R** |
| HA·백업 구성 | A | I | I | C | I | I | I | I | I | **R** |
| 데이터 정합성 검증 잡 | I | I | I | C | C | I | I | I | I | **A/R** |
| 마이그레이션 수행 | I | I | I | C | C | C | I | I | I | **A/R** |

### 3.7 품질 관리·테스트

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 테스트 시나리오 설계 | I | C | I | C | C | C | C | C | **A/R** | C |
| 단위 테스트 작성 | I | I | I | C | **R** | **R** | **R** | **R** | A | I |
| 통합·회귀 테스트 | I | I | I | C | C | C | C | C | **A/R** | I |
| E2E 자동화(Playwright) | I | I | I | C | I | I | C | C | **A/R** | I |
| 부하·안정성 테스트 | A | I | I | C | C | I | I | I | **R** | C |
| 버그 등록·추적 | I | I | I | C | C | C | C | C | **A/R** | I |
| 배포 전 QA 완료 보고 | I | I | I | C | I | I | I | I | **A/R** | I |

### 3.8 배포·운영

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 배포 일정 조율 | **A/R** | C | I | C | C | C | C | C | C | C |
| 배포 승인 | **A/R** | I | I | C | I | I | I | I | C | I |
| 운영 배포 수행 | A | I | I | **R** | C | C | C | C | C | C |
| 릴리즈 노트 작성 | A | C | I | **R** | C | C | C | C | C | C |
| 운영 매뉴얼 작성 | A | C | I | **R** | C | C | C | C | C | C |
| 모니터링 대시보드 구성 | I | I | I | **A/R** | C | I | I | I | I | C |

### 3.9 장애 대응

| 업무 | PM | PL | DS | DL | BS | BD | FS | FD | QA | DBA |
|---|---|---|---|---|---|---|---|---|---|---|
| 장애 1차 감지·접수 | I | I | I | C | R | R | R | R | C | R |
| 장애 대응 총괄(애플리케이션) | I | I | I | **A/R** | C | C | C | C | C | C |
| 장애 대응(DB 계층) | I | I | I | C | I | I | I | I | I | **A/R** |
| 에스컬레이션 | **A/R** | I | I | C | I | I | I | I | I | I |
| Kill Switch 발동 결정 | **A** | I | I | **R** | C | I | I | I | I | I |
| 사후 보고서 작성 | **A/R** | I | I | C | C | C | C | C | C | C |

---

## 4. 의사결정 권한 매트릭스 (요약)

| 결정 사항 | 최종 결정권자 |
|---|---|
| 일정·범위·예산 | PM |
| 기술 아키텍처 | DevLead |
| API·코드 표준 | DevLead |
| DB 스키마·인덱스 | DBA (DevLead 협의) |
| 프론트 컴포넌트 구조 | FrontendSenior (DevLead 기준 제시) |
| UI/UX 디자인 | Designer (Planner 협의) |
| 배포 승인 | PM (QA 완료 보고서 기준) |
| Kill Switch 발동 | DevLead 실행 / PM 사후 승인 |
| 실거래 한도 변경 | PM (DevLead 협의) |

## 5. 협업 규칙

- 한 업무에 A(최종 책임)는 반드시 1명만 지정한다.
- 모든 코드는 PR 기반 진행, DevLead 또는 시니어가 리뷰 후 머지.
- 복잡한 SQL은 작성 전 DBA와 사전 협의 (BackendSenior 주도).
- 디자이너 산출물은 FrontendSenior가 컴포넌트화 가이드를 수립한 뒤 FrontendDev가 구현한다.
- 배포는 QA 완료 보고서 확인 후 PM이 승인한다.
- 장애 시 DBA는 DB 계층, DevLead는 애플리케이션 계층을 각각 총괄한다.
