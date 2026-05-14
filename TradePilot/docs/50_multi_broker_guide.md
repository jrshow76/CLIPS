# 50. 다증권사(Multi-Broker) 어댑터 가이드

TradePilot 은 v1.1 부터 **CREON / KIS / 키움** 3종 증권사 어댑터를 지원한다.
사용자는 본인 선호 증권사로 자동매매를 진행할 수 있으며, 시스템은 주 증권사 장애
시 백업 증권사로 fallback 할 수 있다.

본 문서는 운영자/QA/개발자가 다증권사 환경을 셋업·진단하는 데 필요한 정보를 한
곳에 모은다.

---

## 1. 증권사 3종 비교

| 항목 | CREON (대신증권 Plus) | KIS (한국투자증권) | 키움 OpenAPI+ |
|---|---|---|---|
| API 타입 | COM (Win32 32-bit) | REST + WebSocket | COM/ActiveX (Win32 32-bit) |
| OS 의존성 | **Windows 필수** | OS 무관 (Linux 가능) | **Windows 필수** |
| 게이트웨이 | `creon-gateway/` (포트 9100) | 없음 (백엔드 직접 호출) | `kiwoom-gateway/` (포트 9101) |
| 인증 | 로그인 ID/PW + 공인인증서 | OAuth2 (APPKEY/APPSECRET, 24h 토큰) | 로그인 ID/PW + 공인인증서 |
| 모의/실거래 | 계좌 접두사 분리 | 도메인 분리 (openapi vs openapivts) | 계좌 분리 |
| 호출 제한 | 초당 15건 / 4초당 60건 | 초당 약 20건 | 초당 5건 / 시간당 1000건 |
| 시장 | KOSPI / KOSDAQ | KOSPI / KOSDAQ / NYSE / NASDAQ | KOSPI / KOSDAQ / ELW / ETF |
| 실시간 시세 | StockCur (COM 이벤트) | WebSocket H0STCNT0 | SetRealReg (OCX 이벤트) |
| 호가창 (10단계) | StockJpBid | inquire-asking-price-exp-ccn | OPT10004 등 (현재 v1 미사용) |
| 권장도 | 기존 운영자 호환용 | **신규 권장** | CREON 백업 권장 |
| 운영 비용 | 무료 (대신증권 계좌) | 무료 (한투 계좌) | 무료 (키움 계좌) |
| 제약 | 1초 12건 안전마진 → 매매 빈도 제한 | 토큰 24h, 재발급 시 분산락 | 화면번호 100개 제한, OCX 32-bit |

---

## 2. 아키텍처 요약

```
┌────────────────────────────┐
│  Frontend (Next.js)        │
└─────────────┬──────────────┘
              │
        REST / WS (본체)
              │
┌─────────────▼──────────────────────────────────────────────────┐
│  Backend (Linux)                                              │
│  ┌──────────────────────┐  ┌──────────────────────────────┐   │
│  │ OrderService /       │→ │ get_order_router()           │   │
│  │ KillSwitchService /  │  │  (user.preferred_broker +    │   │
│  │ MarketService        │  │   FallbackOrderRouter)       │   │
│  └──────────────────────┘  └─────┬────────┬────────┬──────┘   │
│                                  │        │        │           │
│                          ┌───────▼──┐ ┌───▼──┐ ┌───▼────┐      │
│                          │ Creon    │ │ KIS  │ │ Kiwoom │      │
│                          │ Live     │ │ Live │ │ Live   │      │
│                          │ Router   │ │ Rtr  │ │ Router │      │
│                          └────┬─────┘ └──┬───┘ └────┬───┘      │
└───────────────────────────────┼──────────┼──────────┼──────────┘
                                │          │          │
                       HTTP +   │   HTTPS  │   HTTP + │
                       Redis    │   (REST) │   Redis  │
                                │          │          │
┌───────────────────────┐  ┌────▼─────┐    │    ┌─────▼────────────┐
│ creon-gateway/        │  │ creon-   │    │    │ kiwoom-gateway/  │
│ (Windows 호스트)      │  │ gateway  │    │    │ (Windows 호스트) │
│ port 9100             │←─┘          │    │    │ port 9101        │←┐
└───────────────────────┘             │    │    └──────────────────┘ │
                                      │    │                          │
                                      │  ┌─▼─────────────────────┐    │
                                      │  │ KIS Open API (외부)   │    │
                                      │  │ openapi.kor...:9443  │    │
                                      │  │ openapivts...:29443  │    │
                                      │  └──────────────────────┘    │
                                      │                              │
              Redis Pub/Sub (tp:*) 채널 — 게이트웨이 → 본체 이벤트 전파
                                                                       
```

핵심:
- ``OrderRouterPort`` / ``MarketDataPort`` 추상 인터페이스로 어댑터 교환 가능.
- 모든 게이트웨이는 동일 Redis 채널(`tp:market.tick.<code>`, `tp:account.execution`, `tp:gateway.healthbeat`)로 이벤트를 publish.
- KIS 는 별도 게이트웨이 없이 백엔드에서 직접 호출 (Linux 호스트 사용 가능).

---

## 3. KIS API 신청 절차

1. **한국투자증권 계좌 개설** (모바일 앱 또는 영업점).
2. **KIS Developers 포털** 가입: <https://apiportal.koreainvestment.com>
3. 모의투자 신청 (별도 페이지) — 8자리 모의 계좌번호 발급.
4. "앱 생성" → ``APPKEY``, ``APPSECRET`` 발급.
5. ``KIS_API_URL_SIM`` (29443) 으로 토큰 발급 검증:
   ```bash
   curl -s -X POST 'https://openapivts.koreainvestment.com:29443/oauth2/tokenP' \
     -H 'Content-Type: application/json' \
     -d '{"grant_type":"client_credentials","appkey":"...","appsecret":"..."}'
   ```
6. ``.env`` 에 다음 항목 채우기:
   - ``KIS_APPKEY`` / ``KIS_APPSECRET``
   - ``KIS_ACCOUNT_NO`` (8자리)
   - ``KIS_ACCOUNT_PROD_CD`` (대개 ``01``)
   - ``KIS_TRADE_ENV=SIM`` (실거래 전환 시 ``REAL``)

---

## 4. 키움 OpenAPI+ 신청 절차

1. **키움증권 계좌 개설**.
2. **키움 OpenAPI+ 사용 신청**: <https://www3.kiwoom.com/h/customer/download/VOpenApiInfoView>
3. 모의투자는 별도 가입 (`https://www3.kiwoom.com/mw/api/htsmodel`).
4. **KOA Studio + OpenAPI 패키지** 설치 (32-bit Python 필수).
5. ``kiwoom-gateway/.env`` 설정:
   - ``KIWOOM_TRADE_ENV=SIM``
   - ``KIWOOM_ACCOUNT_NO`` (계좌 접두사 8 = 모의, 0 = 실거래)
   - ``GATEWAY_API_KEY`` (32자 이상 랜덤)
6. Windows 호스트에서 `scripts/start-gateway.ps1` 으로 기동 + 자동로그인.
7. 본체 ``.env`` 에서 ``KIWOOM_GATEWAY_URL`` / ``KIWOOM_GATEWAY_API_KEY`` 설정.

---

## 5. 사용자 선호 broker 설정 흐름

1. 사용자 로그인 → 설정 화면 진입 (`/settings/brokers`).
2. ``GET /api/v1/settings/brokers`` → 가용 증권사 카탈로그 조회.
3. ``POST /api/v1/settings/brokers/KIS/connect``
   ```json
   {
     "appkey": "...",
     "appsecret": "...",
     "account_no": "12345678",
     "account_prod_cd": "01"
   }
   ```
   → 백엔드는 ``aes_encrypt()`` 로 ``appkey_enc`` / ``appsecret_enc`` 저장.
   응답에는 마스킹된 계좌번호만 노출.
4. ``PUT /api/v1/settings/brokers/preference  {"broker":"KIS"}`` → ``users.preferred_broker`` 갱신.
5. 다음 주문부터 ``get_order_router(LIVE, user=user)`` 가 KIS 라우터를 반환.
6. 해제: ``POST /api/v1/settings/brokers/KIS/disconnect`` → ``broker_credentials.KIS`` 제거.

DB 흐름:
- ``tp_user.users.preferred_broker``: 사용자 선호 (default CREON)
- ``tp_user.users.broker_credentials`` (JSONB):
  ```json
  {
    "KIS":   { "appkey_enc": "…", "appsecret_enc": "…", "account_no": "…", "account_prod_cd": "01", "connected_at": "…" },
    "KIWOOM":{ "account_no": "…", "connected_at": "…" }
  }
  ```

평문 비밀은 **저장 금지**. AES-256-GCM (`security.aes_encrypt`) 만 사용.

---

## 6. Fallback 정책

목적: 주 증권사 게이트웨이 장애로 인한 거래 기회 손실 최소화.

활성화: 환경변수 + 백업 broker 지정.
```bash
BROKER_FALLBACK_ENABLED=true
BROKER_FALLBACK_BACKUP=KIS
```

동작:
- 주 broker ``submit_order`` 가 다음 에러를 raise 하면 백업 broker 로 1회 재시도:
  - ``E0012`` 게이트웨이 미연결
  - ``E0004`` 게이트웨이 내부 오류
  - ``E0072`` 응답 타임아웃
- 비즈니스 거부(증거금 부족 E0024 / 호가단위 E0026 / 거래정지 E0028 등)는
  **fallback 하지 않고** 그대로 사용자에게 전달.
- ``cancel_order`` 는 fallback 하지 않는다. ``broker_order_no`` 가 원래 broker 에
  종속되어 있어 다른 broker 로 취소 요청 시 사고 위험.

운영 모니터링:
- ``broker_fallback_triggered`` 로그를 Prometheus alert 로 추적
- 1시간 내 fallback 5회 이상 → SEV-2 알림

---

## 7. 어댑터 패턴 요약

| 계층 | 인터페이스 | CREON | KIS | KIWOOM |
|---|---|---|---|---|
| 주문 | `OrderRouterPort` | `creon.LiveOrderRouter` | `kis.KisLiveOrderRouter` | `kiwoom.KiwoomLiveOrderRouter` |
| 시세 | `MarketDataPort` | `creon.LiveMarketData` | `kis.KisLiveMarketData` | `kiwoom.KiwoomLiveMarketData` |
| 전송 | — | HTTP → creon-gw | HTTPS → KIS 직접 | HTTP → kiwoom-gw |
| 이벤트 | Redis Pub/Sub | `creon` 라벨 | `kis` 라벨 | `KIWOOM` 라벨 |
| 멱등성 | `X-Idempotency-Key` (gateway) | 게이트웨이 헤더 | `custom_idem` 헤더 | 게이트웨이 헤더 |
| Kill Switch | `cancel_order(timeout=2.0)` 공통 | 동일 시그니처 | 동일 시그니처 | 동일 시그니처 |

핵심: ``OrderRouterPort`` 의 시그니처를 변경하면 안 된다 (3종 어댑터 동시 호환 보장).

---

## 8. 비용 / 제약 비교

| 항목 | CREON | KIS | KIWOOM |
|---|---|---|---|
| 가입비 | 없음 | 없음 | 없음 |
| 월 사용료 | 없음 | 없음 | 없음 |
| 거래 수수료 | 대신증권 표준 | 한투 표준 (Open API 우대 있음) | 키움 표준 |
| 데이터 사용료 | 무료 (개인) | 무료 | 무료 |
| Windows 호스트 비용 | 별도 (소형 PC + 전기료) | 0 (Linux 백엔드) | 별도 |
| 운영 안정성 | 중 (COM 재연결 빈도) | 상 (REST) | 중 (OCX 안정성) |
| 추천 | 기존 사용자 | **신규 권장** | CREON 백업 |

---

## 9. 진단 명령

```bash
# CREON 게이트웨이
curl -s http://10.0.0.20:9100/healthz | jq

# 키움 게이트웨이
curl -s http://10.0.0.21:9101/healthz | jq

# KIS 토큰 발급 (백엔드에서)
docker exec -it tradepilot-backend python -c "
import asyncio
from app.integrations.kis.auth import KisAuth
print(asyncio.run(KisAuth()._call_token_endpoint()))
"

# Redis 헬스비트 구독 (broker 라벨 확인)
redis-cli SUBSCRIBE tp:gateway.healthbeat
```

---

## 10. 관련 문서

- `docs/15_trading_policy.md` — 매매 정책
- `docs/23_creon_gateway.md` — CREON 게이트웨이 명세
- `docs/14_exception_policy.md` — E0xxx 에러 코드 체계
- `qa/63_multi_broker_integration_plan.md` — 다증권사 통합 테스트 계획
- `database/migrations/2026_05_add_broker_settings.sql` — DB 마이그레이션
