# TradePilot

> 한국 주식시장(KOSPI / KOSDAQ) 대상 자동매매 플랫폼
>
> 분석 → 시그널 → 자동매매 → 수익률 추적을 단일 플랫폼에서 제공하는 개인 투자자용 시스템

| 항목 | 값 |
|---|---|
| 버전 | v0.1 (Phase 0 - 설계 완료) |
| 라이선스 | 내부 사용 (개인 한정) |
| 언어 | 한국어 |
| 기술 스택 | Python 3.11 / FastAPI · Next.js 14 / TypeScript · PostgreSQL 15 · Redis 7 · CREON Plus |

---

## 1. 프로젝트 개요

TradePilot은 대신증권 **CREON Plus**(Windows COM)를 통해 한국 주식시장에 자동매매를 수행하는 시스템이다.

- **분석**: MA, RSI, MACD, 볼린저밴드, OBV, VWAP, Stochastic, 섹터 상관관계, LSTM 단기 예측
- **추천**: 멀티 인디케이터 점수 합산형 추천 엔진
- **자동매매**: 시뮬레이션(SIM) ↔ 실거래(LIVE) 단일 코드베이스 + 어댑터 토글
- **리포트**: 일/주/월 수익률, 종목·전략별 성과, MDD, 샤프지수
- **백테스트**: 비동기 큐 기반, 결과 비교/저장

자세한 비전과 범위는 [`docs/00_project_charter.md`](docs/00_project_charter.md)를 참고한다.

---

## 2. 아키텍처 한눈에 보기

```
[ Next.js Web ]  --HTTPS/WS-->  [ Nginx ]  --HTTP-->  [ FastAPI API ]
                                                            |
                                          ┌─────────────────┼────────────────┐
                                          v                 v                v
                                   [ PostgreSQL ]      [ Redis ]      [ Celery Workers ]
                                                            ^                ^
                                                            |                |
                                                            └───── Pub/Sub ──┘
                                                                  |
                                                                  v
                            [ Windows 호스트 ] ───── COM ──── [ CREON Plus ]
                            [ creon-gateway (FastAPI 32-bit) ]
```

- 본체 서비스는 **Linux + Docker**로 구동 (`docker-compose`).
- 크레온 어댑터는 **Windows 별도 호스트**의 `creon-gateway` 프로세스로 격리한다.
- 두 시스템은 동일한 **Redis**를 공유하여 실시간 이벤트(시세 tick, 체결 알림)를 주고받는다.

상세 설계는 [`docs/20_architecture.md`](docs/20_architecture.md)를 참고한다.

---

## 3. 디렉토리 구성

```
TradePilot/
├── backend/                 # FastAPI 백엔드 (BackendSenior가 구현)
├── frontend/                # Next.js 14 프론트엔드 (FrontendSenior가 구현)
├── database/                # 초기화 SQL, 마이그레이션 스크립트
├── design/                  # 디자이너 산출물 (HTML/CSS 퍼블리싱)
├── scripts/                 # 운영 스크립트
├── docs/                    # 기획/설계/정책 문서
│   ├── 00_project_charter.md
│   ├── 01_milestones.md
│   ├── 10_srs.md
│   ├── 11_feature_spec.md
│   ├── 12_screen_flow.md
│   ├── 13_api_requirements.md
│   ├── 14_exception_policy.md
│   ├── 15_trading_policy.md
│   ├── 20_architecture.md          # 시스템 아키텍처
│   ├── 21_backend_structure.md     # 백엔드 디렉토리/레이어
│   ├── 22_frontend_structure.md    # 프론트 디렉토리/상태관리
│   ├── 23_creon_gateway.md         # 크레온 게이트웨이 설계
│   ├── 24_api_response_spec.md     # API 공통 규약
│   └── 25_code_standard.md         # 코드 표준
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. 빠른 시작 (개발 환경)

### 4.1 사전 요구사항

| 도구 | 버전 |
|---|---|
| Docker Engine | 24.x 이상 |
| Docker Compose | v2.x |
| Git | 2.30+ |
| (개발 전용) Python | 3.11 |
| (개발 전용) Node.js | 20.x (LTS) |
| (개발 전용) pnpm | 8.x |

> 크레온 게이트웨이는 별도 Windows 호스트에서 실행한다. 셋업 가이드는 [`docs/23_creon_gateway.md`](docs/23_creon_gateway.md) 참고.

### 4.2 클론 및 환경변수 설정

```bash
git clone https://github.com/<org>/TradePilot.git
cd TradePilot
cp .env.example .env
# .env 파일을 열어 필요한 값(JWT_SECRET, AES_KEY, CREON_GATEWAY_URL 등)을 채운다.
```

### 4.3 서비스 기동

```bash
# 컨테이너 빌드 및 실행
docker compose up -d --build

# 상태 확인
docker compose ps

# 로그 확인 (예: 백엔드)
docker compose logs -f backend-api
```

기본 접근 URL:
- 프론트엔드: http://localhost:3000
- 백엔드 API: http://localhost:8000/api/v1
- API 문서(Swagger): http://localhost:8000/docs (개발 환경 한정)

### 4.4 DB 마이그레이션 (초기 1회)

```bash
docker compose exec backend-api alembic upgrade head
```

### 4.5 기본 사용자 생성 (개발용)

```bash
docker compose exec backend-api python -m app.scripts.create_admin \
  --email admin@local --password admin1234! --role ROLE_ADMIN
```

### 4.6 종료 / 정리

```bash
# 정지
docker compose down

# 볼륨까지 삭제 (데이터 초기화)
docker compose down -v
```

---

## 5. 크레온 게이트웨이 (Windows)

본체 백엔드는 실거래 모드 시 별도 Windows 호스트의 `creon-gateway`와 통신한다.

1. Windows 10/11 Pro 64-bit 호스트 준비.
2. CREON Plus 설치 및 로그인 (자동 로그인 권장).
3. Python 3.11 **32-bit** 설치.
4. `creon-gateway/` 디렉토리(별도 저장소 또는 본 저장소 하위)의 `requirements.txt` 설치.
5. NSSM으로 Windows 서비스 등록 (포트 9100 기본).
6. 메인 서버의 `.env`에 `CREON_GATEWAY_URL`, `CREON_GATEWAY_API_KEY` 설정.

상세 절차: [`docs/23_creon_gateway.md`](docs/23_creon_gateway.md).

---

## 6. 매매 모드 (SIM / LIVE)

- 기본 모드는 **SIM(시뮬레이션)** 이다.
- 실거래(LIVE) 전환은 다음 조건을 모두 충족해야 한다 ([`docs/15_trading_policy.md`](docs/15_trading_policy.md) §2.1):
  1. 본인인증 완료(이메일 + 휴대전화)
  2. OTP 6자리 인증
  3. 약관/면책 동의
  4. 일일/종목 한도 1회 이상 저장
  5. 시뮬레이션 누적 거래 30건 이상
  6. CREON COM 연결 테스트 성공
- UI에는 모드 배지가 항상 표시되며 (SIM=파랑, LIVE=빨강), 주요 액션은 2단계 확인을 거친다.
- 위험 상황에서는 **Kill Switch**로 즉시 모든 주문을 취소하고 SIM으로 강제 전환할 수 있다.

---

## 7. 주요 문서 인덱스

| 분류 | 문서 | 작성자 |
|---|---|---|
| 프로젝트 | [`00_project_charter.md`](docs/00_project_charter.md) | PM |
| 일정 | [`01_milestones.md`](docs/01_milestones.md) | PM |
| 리스크 | [`02_risks.md`](docs/02_risks.md) | PM |
| RACI | [`03_team_raci.md`](docs/03_team_raci.md) | PM |
| 릴리즈 | [`04_release_plan.md`](docs/04_release_plan.md) | PM |
| 요구사항 | [`10_srs.md`](docs/10_srs.md) | Planner |
| 기능 정의 | [`11_feature_spec.md`](docs/11_feature_spec.md) | Planner |
| 화면 흐름 | [`12_screen_flow.md`](docs/12_screen_flow.md) | Planner |
| API 요구사항 | [`13_api_requirements.md`](docs/13_api_requirements.md) | Planner |
| 예외 처리 | [`14_exception_policy.md`](docs/14_exception_policy.md) | Planner |
| 매매 정책 | [`15_trading_policy.md`](docs/15_trading_policy.md) | Planner |
| 시스템 아키텍처 | [`20_architecture.md`](docs/20_architecture.md) | DevLead |
| 백엔드 구조 | [`21_backend_structure.md`](docs/21_backend_structure.md) | DevLead |
| 프론트엔드 구조 | [`22_frontend_structure.md`](docs/22_frontend_structure.md) | DevLead |
| 크레온 게이트웨이 | [`23_creon_gateway.md`](docs/23_creon_gateway.md) | DevLead |
| API 공통 규약 | [`24_api_response_spec.md`](docs/24_api_response_spec.md) | DevLead |
| 코드 표준 | [`25_code_standard.md`](docs/25_code_standard.md) | DevLead |

---

## 8. 개발 워크플로우

1. 이슈 등록 (요구사항/버그) → DevLead가 우선순위 협의.
2. `feature/<scope>-<desc>` 브랜치 생성.
3. 코드 작성 + 단위 테스트 추가 ([`docs/25_code_standard.md`](docs/25_code_standard.md) 준수).
4. Pull Request 생성 → CI(lint/test/build) 통과 → 리뷰 → squash merge.
5. main 머지 시 스테이징 자동 배포 (GitHub Actions).
6. QA 통과 → PM 배포 승인 → 운영 반영.

---

## 9. 라이선스 / 책임 고지

- 본 프로젝트는 내부 사용 한정이다. 외부 서비스화 및 재배포는 금지된다.
- 자동매매로 발생하는 손익에 대한 최종 책임은 사용자 본인에게 있다.
- 자본시장법상 투자자문업/일임업 라이선스 없이는 외부 제공이 불가하다.

---

## 10. 연락 / 기여

- 기술 이슈: GitHub Issues
- 보안 취약점: 비공개 채널(DevLead 직접 연락)
- 정책 변경 제안: PM 승인 절차 ([`docs/15_trading_policy.md`](docs/15_trading_policy.md) §12)

---

## 11. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v0.1 | 2026-05-12 | DevLead | 초기 README 작성 (Phase 0 설계 완료 시점) |
