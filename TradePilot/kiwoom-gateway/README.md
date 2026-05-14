# TradePilot Kiwoom Gateway

키움증권 OpenAPI+ 어댑터 게이트웨이 (Windows 전용).
CREON 게이트웨이와 동일한 책임 분리/패턴을 따르며, 본체(`backend`)는 HTTP 로 호출한다.

## 책임

- 키움 OpenAPI+ OCX (`KHOPENAPI.KHOpenAPICtrl.1`) 호스팅
- SIM(모의) / REAL(실거래) 분기 (계좌번호 + 환경변수)
- 초당/시간당 호출 한도 보호 (Rate Limiter, sliding window)
- 표준 응답 envelope `{success, data, raw}` 또는 `{success: false, error}` 반환
- Redis Pub/Sub 으로 체결/시세 이벤트 본체에 전파
- 헬스비트 30초 주기 발행

## 디렉토리 구조

```
kiwoom-gateway/
├─ pyproject.toml
├─ .env.example
├─ README.md
├─ kiwoom_gateway/
│  ├─ __init__.py
│  ├─ config.py            # 환경설정 (Pydantic Settings)
│  ├─ event_publisher.py   # Redis Pub/Sub 발행
│  ├─ healthbeat.py        # 헬스비트 백그라운드 태스크
│  ├─ kiwoom_adapter.py    # Mock / Real (PyQt5 QAxWidget) 어댑터
│  └─ main.py              # FastAPI 엔드포인트
├─ scripts/
│  ├─ start-gateway.ps1    # 자동 기동
│  ├─ cpStartup-template.bat
│  └─ register-task.ps1    # Windows 작업 스케줄러 등록
└─ tests/
   └─ test_kiwoom_adapter.py
```

## 사전 준비 (Windows 운영자)

1. **32-bit Python 3.8** 설치 (키움 OCX 가 64-bit 미지원).
2. 가상환경 생성: `python -m venv C:\tradepilot\.venv-x86`.
3. 키움 OpenAPI+ 설치 (https://www3.kiwoom.com/h/customer/download/VOpenApiInfoView).
4. KOA Studio 1회 실행 → 자동로그인 도구 설정.
5. 본 디렉토리 복사: `xcopy /E kiwoom-gateway C:\tradepilot\kiwoom-gateway`.
6. 의존성 설치:
   ```powershell
   cd C:\tradepilot\kiwoom-gateway
   C:\tradepilot\.venv-x86\Scripts\pip install -e .[windows]
   ```
7. `.env.example` → `.env` 복사 후 값 채우기 (특히 `GATEWAY_API_KEY`, `KIWOOM_ACCOUNT_NO`).
8. 자동 기동 등록 (관리자 PowerShell):
   ```powershell
   .\scripts\register-task.ps1 -AlsoOnBoot
   ```

## Linux/Mac 개발 환경 (Mock 모드)

비-Windows 환경에서는 자동으로 `MockKiwoomAdapter` 가 사용된다.

```bash
cd kiwoom-gateway
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
# .env 에서 KIWOOM_FORCE_MOCK=true 가 기본
uvicorn kiwoom_gateway.main:app --host 0.0.0.0 --port 9101
```

테스트:
```bash
pytest -q tests/
```

## 엔드포인트

CREON 게이트웨이 (`docs/23_creon_gateway.md`) §5 와 거의 동일한 형상이며, 추가로
`broker=KIWOOM` 라벨을 헬스비트/이벤트에 포함한다.

| Method | Path | 설명 |
|---|---|---|
| GET  | /healthz                  | liveness (인증 불필요) |
| GET  | /readyz                   | readiness — connected + account_loaded |
| GET  | /system/status            | 어댑터 상세 상태 |
| POST | /system/reconnect         | 강제 재연결 |
| POST | /orders                   | 주문 발주 (idempotency-key 지원) |
| POST | /orders/{id}/cancel       | 주문 취소 |
| GET  | /account                  | 계좌 목록 |
| GET  | /account/balance          | 예수금/평가 |
| GET  | /account/positions        | 보유 종목 |
| GET  | /market/quote/{code}      | 현재가 |
| POST | /subscribe/quote          | 실시간 시세 구독 |
| POST | /unsubscribe/quote        | 구독 해제 |

## 에러 코드 매핑 (raw → K0xxx)

| 키움 raw | 표준 G/K 코드 | 의미 |
|---|---|---|
| -10  | K0001 | 미접속 |
| -101 | K0002 | 서버 접속 실패 |
| -200 | K0010 | 호출 한도 초과 |
| -201 | K0011 | 주문가격 오류 |
| -202 | K0012 | 주문수량 오류 |
| -300 | K0013 | 주문 입력 오류 |
| -301 | K0014 | 계좌 비밀번호 오류 |

본체(`backend/app/integrations/kiwoom/client.py`) 는 K0xxx → Exxxx 매핑을 추가 적용.

## 보안

- `X-Gateway-Api-Key` 헤더 timing-safe 검증.
- 키 미설정/placeholder/32자 미만이면 503 (fail-fast).
- 평문 비밀번호를 git/.env 평문 저장 금지. `KIWOOM_ACCOUNT_PWD_ENCRYPTED` 는 AES-256-GCM 토큰만 저장.

## 참고 문서

- `docs/23_creon_gateway.md` — CREON 게이트웨이 (동일 패턴)
- `docs/50_multi_broker_guide.md` — 다증권사 비교 + 사용자 설정 흐름
- `qa/63_multi_broker_integration_plan.md` — 통합 테스트 계획
