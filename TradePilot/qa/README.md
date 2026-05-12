# TradePilot QA 디렉토리 안내

본 디렉토리는 TradePilot의 품질 보증(QA) 산출물을 모은 작업 공간이다. 모든 문서·테스트는 한글로 작성되며, 실거래 사고 방지에 우선순위를 둔다.

## 디렉토리 구성

```
qa/
├── README.md                       # 본 파일
├── 50_test_strategy.md             # 테스트 전략(피라미드/환경/도구/커버리지 목표)
├── 51_test_cases.md                # 테스트 케이스 카탈로그(도메인별 표, 100건 이상)
├── 52_trading_policy_tests.md      # 매매 정책 회귀(LIVE 게이트, Kill Switch, 한도)
├── 53_exception_matrix.md          # 40개 에러 코드 회귀 매트릭스
├── 54_release_checklist.md         # Alpha/Beta/v1.0 게이트별 릴리즈 체크리스트
├── 55_bug_template.md              # 버그 리포트 템플릿
├── e2e/                            # Playwright E2E 자동화
│   ├── package.json
│   ├── playwright.config.ts
│   ├── tests/                      # 시나리오별 spec
│   └── README.md
└── load/                           # 부하/스모크 테스트
    ├── smoke.sh
    ├── k6_orders_burst.js
    └── README.md
```

## 백엔드 QA 테스트

백엔드 QA 회귀 테스트는 `backend/tests/qa/`에 위치한다(pytest + 기존 `conftest.py` 픽스처 재사용).

```
backend/tests/qa/
├── __init__.py
├── test_trade_mode_guard.py        # X-Trade-Mode/E0006/LIVE 게이트
├── test_kill_switch.py             # Kill Switch SLA·강제 SIM 전환
├── test_trade_limits.py            # 일일/주문당 한도 E0021/E0026
├── test_idempotency.py             # X-Idempotency-Key 24h
├── test_rate_limit.py              # 4티어 슬라이딩 윈도우
├── test_indicator_correctness.py   # 골든크로스/RSI/MACD 정확성
├── test_pagination_response.py     # 페이지네이션·응답 envelope
└── test_security_jwt_otp.py        # JWT 위변조·OTP 5분 만료
```

## 작업 절차

1. 새로운 기능이 머지되면 `51_test_cases.md`의 해당 도메인 표에 케이스를 추가한다.
2. 매매 정책이 변경되면 PM 승인 후 `52_trading_policy_tests.md`를 갱신한다.
3. 신규 에러 코드는 `53_exception_matrix.md`에 즉시 등록한다.
4. 릴리즈 시 `54_release_checklist.md`의 해당 게이트 항목을 모두 체크한다.
5. 버그는 `55_bug_template.md` 양식으로 Jira에 등록한다.

## 우선순위 표기

| 우선순위 | 정의 | 자동화 여부 |
|---|---|---|
| P0 | 실거래 사고와 직결, 릴리즈 차단 | 자동화 필수 |
| P1 | 핵심 기능, 정상 흐름 | 자동화 권장 |
| P2 | 일반 기능, 보조 시나리오 | 수동 가능 |

## 보고 라인

- 일일 QA 결과: `QA → DevLead`
- 릴리즈 게이트 통과 보고: `QA → PM`
- 데이터 정합성 의심 사례: `QA → DBA`(DB 직접 조회 협의)

## 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | QA | 최초 작성 |
