# TradePilot E2E 실행 가이드 (Playwright)

본 디렉토리는 Playwright 기반 E2E 자동화 스위트이다. 다중 브라우저(Chromium/Firefox/WebKit) + 모바일 viewport 회귀를 포함한다.

## 사전 준비

```bash
cd qa/e2e
npm install
npx playwright install --with-deps
```

> 한국어 로케일 폰트가 필요한 경우 `playwright install --with-deps` 가 자동 설치한다.

## 실행 환경

- 프론트엔드는 mock 모드로 기동: `NEXT_PUBLIC_USE_MOCK=true npm run dev` (포트 3000).
- 기본 base URL: `http://localhost:3000`. 변경 시 `E2E_BASE_URL=...` 환경변수 사용.
- E2E 헤더 `X-E2E: true` 가 모든 요청에 자동 첨부됨.

```bash
cd frontend
NEXT_PUBLIC_USE_MOCK=true npm run dev   # 별도 터미널
```

## 실행 명령어

```bash
# 전체 (모든 projects)
npm test

# 단일 브라우저
npm run test:chromium

# 모바일 프로젝트
npm run test:mobile

# 디버그(헤드드)
npm run test:headed

# HTML 리포트 보기
npm run report
```

## 스위트 구성

| 파일 | 우선순위 | 설명 |
|---|:---:|---|
| `tests/auth.spec.ts` | P0 | 로그인/회원가입/OTP |
| `tests/dashboard.spec.ts` | P1 | 대시보드 위젯 |
| `tests/chart.spec.ts` | P1 | 차트/지표 |
| `tests/auto-trading.spec.ts` | P0 | 전략·LIVE 전환·Kill Switch |
| `tests/live-mode-modal.spec.ts` | P0 | LIVE 전환 이중확인 모달 |
| `tests/responsive.spec.ts` | P1 | 320/768/1280 viewport |
| `tests/notifications.spec.ts` | P1 | 알림 센터 |

## CI 통합

GitHub Actions 워크플로 (`.github/workflows/e2e.yml`) 예시:

```yaml
- run: cd qa/e2e && npm ci
- run: cd qa/e2e && npx playwright install --with-deps
- run: cd qa/e2e && npm test
```

- 실패 시 `playwright-report/` 디렉토리 아티팩트 업로드.
- JUnit 리포트(`reports/junit.xml`) 는 Jira 연동에 사용.

## 결함 발견 시

1. `qa/55_bug_template.md` 양식으로 Jira 이슈 등록.
2. 실패 스크린샷/트레이스 첨부 (`test-results/` 자동 생성).
3. 회귀가 필요한 경우 spec 파일에 신규 케이스 추가.
