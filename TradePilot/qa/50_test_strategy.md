# TradePilot 테스트 전략 (Test Strategy)

> 문서 ID: 50_TEST_STRATEGY
> 버전: v1.0
> 작성자: QA
> 최종 수정일: 2026-05-12

본 문서는 TradePilot 전체 품질 보증을 위한 테스트 전략, 환경, 도구, 우선순위, 커버리지 목표를 정의한다. 실거래 사고 방지를 최우선 목표로 한다.

---

## 1. 품질 목표

| 항목 | 목표 |
|---|---|
| 실거래 사고(오발주/과대 주문) | 0건 (P0 항목 100% 자동화) |
| 핵심 기능(P0) 회귀 자동화 비율 | 100% |
| 전체 기능(P0+P1+P2) 자동화 비율 | 60% 이상 |
| 백엔드 단위 테스트 커버리지 | 70% 이상 (`pytest --cov`) |
| 백엔드 핵심 모듈(주문/리스크/모드) 커버리지 | 90% 이상 |
| Critical/High 결함 잔존 (릴리즈 시점) | 0건 |
| E2E 회귀 통과율 (Alpha/Beta 게이트) | 100% |

---

## 2. 테스트 피라미드

```
                /\
               /E2\         <- Playwright (qa/e2e/) : 15~25개 시나리오
              /----\
             / 통합 \        <- pytest integration : 도메인별 50~80건
            /--------\
           /  단위    \      <- pytest unit + QA 회귀 : 200건+
          /------------\
```

| 레벨 | 도구 | 범위 | 비중 |
|---|---|---|---|
| 단위 | pytest (`backend/tests/unit/`) | 함수/클래스 단위(지표, 보안, SimRouter, 정책 객체) | 70% |
| 통합 | pytest (`backend/tests/integration/`, `backend/tests/qa/`) | API 라우터, DB·Redis 연동, 인증 흐름 | 25% |
| E2E | Playwright (`qa/e2e/`) | 사용자 시나리오, 다중 브라우저, 모바일 viewport | 5% |
| 부하/스모크 | k6, curl 스크립트 (`qa/load/`) | RPS·응답시간·핵심 GET 200 응답 | 보조 |

> 매매 정책·실거래 사고 방지 영역은 단위·통합·E2E 모두에서 다중 검증한다.

---

## 3. 테스트 환경

### 3.1 환경별 분리
| 환경 | 매매 모드 | 외부 의존성 | 데이터 |
|---|---|---|---|
| Dev (로컬) | SIM | Mock CREON, 로컬 PostgreSQL/Redis | 샘플 시드 |
| QA / Staging | SIM(기본) + LIVE 시뮬레이션 토글 | 모의 게이트웨이 + 시뮬 CREON | 실시세 미러(15분 지연) |
| Production | SIM / LIVE 정식 | 실 CREON Plus (Windows 호스트 이중화) | 실시간 |

### 3.2 테스트 데이터 정책
- 통합 테스트는 `testcontainers` 또는 `docker compose -f docker-compose.test.yml`로 격리된 PostgreSQL/Redis 사용.
- 시드 데이터: `database/seeds/`의 종목 마스터(005930, 000660 등 30종목), 일/분봉 30영업일 분량.
- E2E는 프론트엔드 mock 모드(`NEXT_PUBLIC_USE_MOCK=true`)로 백엔드 의존 없이 실행한다.
- 민감정보(이메일, 휴대전화)는 마스킹 후 fixture로 제공한다(`@test.local` 도메인 사용).

### 3.3 시간 의존성
- 매매 운영 시간(09:00~15:20) 의존 테스트는 freezegun으로 KST 시각 고정.
- 일일 한도/카운터 리셋은 KST 자정 기준 가짜 시계로 검증.

---

## 4. 도구 스택

| 영역 | 도구 |
|---|---|
| 백엔드 단위/통합 테스트 | pytest, pytest-asyncio, httpx |
| 커버리지 | pytest-cov |
| API 수동 탐색 | Postman / Newman (`qa/postman/`, 향후 추가) |
| E2E | Playwright (Chromium/WebKit/Firefox) |
| 부하 | k6 |
| 스모크 | curl + jq |
| 시계 가짜 | freezegun |
| 이슈 트래커 | Jira (프로젝트 키: `TP-`) |
| CI | GitHub Actions (`.github/workflows/`) |

---

## 5. 우선순위 정책

| 우선순위 | 정의 | 사례 | 자동화 |
|---|---|---|---|
| P0 | 실거래 사고 직결 / 릴리즈 차단 | LIVE 게이트 7단계, Kill Switch, 한도, X-Trade-Mode 검증, JWT/OTP 보안 | 필수 |
| P1 | 핵심 기능 정상 흐름 / 사용자 영향 큼 | 로그인, 주문 SIM 체결, 차트 조회, 대시보드, 알림 | 권장 |
| P2 | 일반 기능 / 보조 시나리오 | 즐겨찾기, CSV 내보내기, 다국어, 화면 미세 검증 | 수동 가능 |

- P0는 모든 릴리즈 게이트에서 100% 통과 필수.
- P1은 회귀 자동화 80% 이상 유지.
- P2는 분기 1회 수동 회귀.

---

## 6. 테스트 종류별 책임

| 종류 | 책임 | 산출물 |
|---|---|---|
| 기능 테스트 | QA | `51_test_cases.md` |
| 정책 회귀 | QA | `52_trading_policy_tests.md` |
| 예외 처리 회귀 | QA | `53_exception_matrix.md` |
| 단위 테스트 작성 | Backend/Frontend 개발자 | `tests/unit/` |
| 통합 테스트 작성 | BackendSenior/BackendDev | `tests/integration/` |
| QA 회귀 자동화 | QA | `backend/tests/qa/`, `qa/e2e/` |
| 부하 테스트 | QA + BackendSenior 협업 | `qa/load/` |
| 데이터 정합성 검증 | QA + DBA 협업 | DB SELECT 쿼리(결과 첨부) |

---

## 7. 입출구 기준 (Entry / Exit Criteria)

### 7.1 테스트 진입 기준 (Entry)
- 기능 명세서(`11_feature_spec.md`)와 API 문서(`13_api_spec.md`) 확정.
- BackendDev/BackendSenior 단위 테스트 통과 보고.
- Staging 환경에 빌드 배포 + 헬스체크 200.

### 7.2 테스트 종료 기준 (Exit)
- P0 케이스 100% 통과 + P1 케이스 95% 이상 통과.
- Critical/High 결함 0건.
- 릴리즈 체크리스트(`54_release_checklist.md`) 해당 게이트 전부 체크.
- 회귀 테스트 자동화 그린.

---

## 8. 결함 관리 흐름

1. QA가 결함 발견 → `55_bug_template.md` 양식으로 Jira 등록.
2. DevLead 우선순위 협의 (P0/P1/P2 + 담당 개발자 배정).
3. 개발자 수정 + 단위 테스트 추가 → PR.
4. QA 재현 시나리오 재검증.
5. 닫기 전 회귀 자동화 케이스로 등록(P0/P1).

### 8.1 우선순위와 SLA
| 우선순위 | 1차 응답 | 수정 SLA |
|---|---|---|
| Blocker(매매 사고/로그인 불가) | 즉시 | 4시간 |
| Critical(주요 기능 불가) | 30분 | 1영업일 |
| Major(부분 기능 불가) | 4시간 | 3영업일 |
| Minor(UI/문구) | 1일 | 다음 릴리즈 |

---

## 9. 자동화 운영 정책

- 모든 자동화는 `main` 브랜치 PR 시 GitHub Actions에서 실행.
- 백엔드 QA 회귀(`backend/tests/qa/`)는 `pytest -m "qa or integration"`로 실행.
- E2E는 야간 1회 + Beta/v1.0 게이트 시점 강제 실행.
- 실패 시 Slack `#qa-alert` 채널 알림.
- 부하 테스트(k6)는 주 1회 + 릴리즈 D-1에 수동 실행.

---

## 10. 리스크 기반 테스트 강화 항목 (R-02 연계)

다층 안전망 검증(`02_risks.md` R-02 대응) - 모두 P0:

1. **주문 수량 한도** 회귀: 단일 종목/일일 누적 (E0021).
2. **일일 손실 한도** 회귀: -3% 도달 시 자동 OFF.
3. **이중 확인 모달** E2E: 비밀번호 + 동의 문구 입력 강제.
4. **Kill Switch** 5초 SLA 회귀.
5. **사전 시뮬레이션 의무** 회귀: 30건 미만 시 LIVE 차단(E0016).
6. **소액 한도 단계** 회귀: Beta 일일 100만원 하드 캡.
7. **Pre-flight 체크** 회귀: 잔고/종목/시장 상태 검증.

---

## 11. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | QA | 최초 작성 |
