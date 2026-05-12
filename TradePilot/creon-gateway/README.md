# TradePilot creon-gateway

CREON Plus(Windows COM API)를 본체 백엔드와 격리하기 위한 별도 FastAPI 프로세스.

> 본 게이트웨이는 **Windows 10/11 (32-bit Python 3.11) 호스트**에서만 정상 동작한다.
> Linux/Docker 환경에서는 mock 어댑터로 fallback하여 개발/테스트가 가능하다.

상세 설계: `docs/23_creon_gateway.md`

## 사전 요구 사항 (운영 환경)

| 항목 | 값 |
|---|---|
| OS | Windows 10/11 Pro 64-bit (호스트), 프로세스는 32-bit |
| Python | 3.11 (32-bit `python-3.11.x-win32.exe`) |
| CREON Plus | 대신증권 CREON Plus 설치 + GUI 로그인 상태 유지 |
| 시간 동기화 | NTP 활성, KST |
| 권한 | 관리자 권한 (COM 등록) |
| 절전 모드 | 꺼짐 (장중 휴면 방지) |

## 설치 (Windows)

```powershell
py -3.11-32 -m venv C:\tradepilot\.venv
C:\tradepilot\.venv\Scripts\activate
pip install -e .[windows]
```

## 환경변수 (`.env`)

```env
REDIS_URL=redis://10.0.0.10:6379/0
GATEWAY_API_KEY=long-random-string

GATEWAY_ID=primary
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=9100

CREON_ACCOUNT_NO=12345678
CREON_ACCOUNT_KIND=01
SUBSCRIBE_MAX_CODES=400
RATE_LIMIT_PER_SEC=10

LOG_LEVEL=INFO
```

## 실행

### 개발/테스트 (mock 모드)

```bash
# Linux/Windows 어느 환경에서도 동작 (실제 주문 발생 없음)
uvicorn creon_gateway.main:app --host 0.0.0.0 --port 9100 --reload
```

mock 모드 자동 활성화 조건:
- pywin32 import 실패
- `CREON_FORCE_MOCK=true` 환경변수 설정

### 운영 (Windows + NSSM 서비스)

```powershell
nssm install TradePilotGateway "C:\tradepilot\.venv\Scripts\python.exe" "-m" "uvicorn" "creon_gateway.main:app" "--host" "0.0.0.0" "--port" "9100"
nssm set TradePilotGateway AppDirectory "C:\tradepilot\creon-gateway"
nssm start TradePilotGateway
```

## 컨테이너화 안내

CREON COM은 Windows 전용 GUI 의존성이 있어 Docker 컨테이너화가 **불가**하다.
별도 Windows 호스트(VM 또는 물리 서버)에서 네이티브 실행한다.

자세한 설치 안내: `docs/23_creon_gateway.md` §3.

## API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/healthz` | liveness |
| GET | `/readyz` | COM 세션 readiness |
| GET | `/system/status` | 상세 상태 |
| POST | `/system/reconnect` | COM 강제 재연결 |
| POST | `/orders` | 주문 발주 |
| POST | `/orders/{id}/cancel` | 주문 취소 |
| GET | `/account/balance` | 잔고 |
| GET | `/account/positions` | 보유 |
| GET | `/market/quote/{code}` | 현재가 |

모든 요청은 `X-Gateway-Api-Key` 헤더 필수.

## Redis Pub/Sub 채널 (발행)

- `tp:market.tick.{code}` - 실시간 시세
- `tp:account.execution` - 체결 이벤트
- `tp:account.order_update` - 주문 상태 변경
- `tp:gateway.healthbeat` - 30초 헬스비트
- `tp:gateway.alert` - 경고

상세 메시지 스키마: `docs/23_creon_gateway.md` §6.
