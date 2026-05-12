# TradePilot 백엔드 디렉토리 구조 (Backend Structure)

> 문서 ID: 21_BACKEND_STRUCTURE
> 버전: v1.0
> 작성자: DevLead
> 최종 수정일: 2026-05-12

본 문서는 FastAPI 기반 백엔드의 패키지 구조, 레이어별 책임, 의존성 규칙을 정의한다. 모든 백엔드 개발자는 본 구조를 따라야 하며, 변경 시 DevLead의 승인이 필요하다.

---

## 1. 설계 원칙

### 1.1 레이어드 + 헥사고날 일부 채택

```
[ api ] → [ services ] → [ domains ] ← [ repositories ] → [ DB ]
                ↓
         [ integrations ] → [ creon-gateway, SMTP, ... ]
                ↑
            [ ports ]
```

- **단방향 의존**: 외부 계층은 내부 계층을 알 수 있지만, 내부 계층은 외부 계층을 모른다.
- **포트(인터페이스) 의존**: `services`와 `domains`는 외부 통합(integrations)을 직접 호출하지 않고 `domain.ports`를 통해 추상화한다.
- **DTO ≠ Domain Entity**: API 입출력은 Pydantic Schema, 비즈니스 로직은 Domain Entity로 분리한다.

### 1.2 의존성 규칙 (Dependency Rule)

| 계층 | 허용 import | 금지 import |
|---|---|---|
| `api` | `services`, `schemas`, `core` | `repositories`, `integrations` 직접 호출 금지 |
| `services` | `domains`, `repositories`(인터페이스만), `core` | `api`, FastAPI 의존성 |
| `domains` | 표준 라이브러리, `pydantic`(엔티티만) | 모든 외부 |
| `repositories` | `models`, `db`, `domains.entities` | `services`, `api` |
| `integrations` | `domains.ports`, HTTP/COM 클라이언트 | `services`, `api` |
| `workers` | `services`, `core` | `api` |

---

## 2. 디렉토리 트리

```
backend/
├── pyproject.toml
├── poetry.lock
├── Dockerfile                  # BackendSenior 작성 예정
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── app/
    ├── __init__.py
    ├── main.py                 # FastAPI 엔트리포인트
    ├── celery_app.py           # Celery 인스턴스
    ├── scheduler_app.py        # APScheduler 엔트리포인트
    │
    ├── core/                   # 공통 인프라
    │   ├── __init__.py
    │   ├── config.py           # Pydantic Settings (.env 로드)
    │   ├── logging.py          # 구조화 로그 설정
    │   ├── security.py         # JWT, bcrypt, OTP
    │   ├── deps.py             # FastAPI Depends (인증, DB, 캐시)
    │   ├── exceptions.py       # AppException, 에러 코드 매핑
    │   ├── middleware.py       # TraceId, X-Trade-Mode, RateLimit
    │   ├── pagination.py       # 페이지네이션 유틸
    │   └── time.py             # KST/UTC 변환
    │
    ├── api/                    # 프레젠테이션 계층 (FastAPI 라우터)
    │   ├── __init__.py
    │   ├── router.py           # /api/v1 라우터 통합
    │   ├── v1/
    │   │   ├── __init__.py
    │   │   ├── auth.py
    │   │   ├── users.py
    │   │   ├── stocks.py
    │   │   ├── indicators.py
    │   │   ├── sectors.py
    │   │   ├── recommendations.py
    │   │   ├── signals.py
    │   │   ├── strategies.py
    │   │   ├── orders.py
    │   │   ├── portfolios.py
    │   │   ├── backtest.py
    │   │   ├── ml_predictions.py
    │   │   ├── market.py
    │   │   ├── notifications.py
    │   │   ├── settings.py
    │   │   ├── reports.py
    │   │   ├── admin.py
    │   │   └── ws.py           # WebSocket 핸들러
    │   └── deps/
    │       ├── auth.py         # require_user, require_role
    │       └── trade_mode.py   # X-Trade-Mode 가드
    │
    ├── schemas/                # Pydantic v2 DTO
    │   ├── __init__.py
    │   ├── common.py           # Page, Response, ErrorBody
    │   ├── auth.py
    │   ├── user.py
    │   ├── stock.py
    │   ├── indicator.py
    │   ├── signal.py
    │   ├── strategy.py
    │   ├── order.py
    │   ├── portfolio.py
    │   ├── backtest.py
    │   ├── ml.py
    │   ├── market.py
    │   ├── notification.py
    │   └── setting.py
    │
    ├── services/               # 애플리케이션 서비스 (유스케이스)
    │   ├── __init__.py
    │   ├── auth_service.py
    │   ├── user_service.py
    │   ├── stock_service.py
    │   ├── indicator_service.py
    │   ├── sector_service.py
    │   ├── recommendation_service.py
    │   ├── signal_service.py
    │   ├── strategy_service.py
    │   ├── order_service.py            # SimRouter/LiveRouter 선택
    │   ├── risk_guard.py               # 한도/리스크 검증
    │   ├── portfolio_service.py
    │   ├── backtest_service.py
    │   ├── ml_service.py
    │   ├── notification_service.py
    │   ├── trade_mode_service.py       # SIM↔LIVE 전환 게이트
    │   └── report_service.py
    │
    ├── domains/                # 도메인 계층 (순수 비즈니스)
    │   ├── __init__.py
    │   ├── entities/
    │   │   ├── user.py
    │   │   ├── stock.py
    │   │   ├── order.py
    │   │   ├── signal.py
    │   │   ├── strategy.py
    │   │   ├── portfolio.py
    │   │   ├── backtest.py
    │   │   └── ml.py
    │   ├── enums/
    │   │   ├── trade_mode.py           # SIM | LIVE
    │   │   ├── order_status.py         # NEW | ACCEPTED | FILLED | CANCELED | REJECTED
    │   │   ├── side.py                 # BUY | SELL
    │   │   └── role.py
    │   ├── ports/                      # 외부 의존성 인터페이스
    │   │   ├── order_router.py         # OrderRouterPort
    │   │   ├── market_data.py          # MarketDataPort
    │   │   ├── notification_channel.py # NotificationChannelPort
    │   │   └── ml_model.py             # MLModelPort
    │   ├── rules/                      # 전략 DSL 평가기
    │   │   ├── dsl_parser.py
    │   │   ├── evaluator.py
    │   │   └── operators.py
    │   ├── indicators/                 # 지표 계산 순수 함수
    │   │   ├── ma.py
    │   │   ├── rsi.py
    │   │   ├── macd.py
    │   │   ├── bollinger.py
    │   │   ├── obv.py
    │   │   ├── vwap.py
    │   │   └── stochastic.py
    │   └── policies/
    │       ├── risk_policy.py          # 한도/리스크 정책 객체
    │       └── fee_policy.py
    │
    ├── repositories/           # 데이터 접근 계층
    │   ├── __init__.py
    │   ├── base.py             # BaseRepository<T>
    │   ├── user_repository.py
    │   ├── stock_repository.py
    │   ├── candle_repository.py
    │   ├── tick_repository.py
    │   ├── order_repository.py
    │   ├── execution_repository.py
    │   ├── portfolio_repository.py
    │   ├── signal_repository.py
    │   ├── strategy_repository.py
    │   ├── recommendation_repository.py
    │   ├── backtest_repository.py
    │   ├── ml_repository.py
    │   ├── notification_repository.py
    │   └── audit_log_repository.py
    │
    ├── models/                 # SQLAlchemy 2.x ORM 모델
    │   ├── __init__.py
    │   ├── base.py             # DeclarativeBase, timestamps mixin
    │   ├── user.py
    │   ├── stock.py
    │   ├── candle.py
    │   ├── tick.py
    │   ├── order.py
    │   ├── execution.py
    │   ├── portfolio.py
    │   ├── signal.py
    │   ├── strategy.py
    │   ├── recommendation.py
    │   ├── backtest.py
    │   ├── ml_model.py
    │   ├── notification.py
    │   └── audit_log.py
    │
    ├── db/
    │   ├── __init__.py
    │   ├── session.py          # AsyncSession factory
    │   ├── engine.py
    │   └── unit_of_work.py     # 트랜잭션 컨텍스트
    │
    ├── integrations/           # 외부 시스템 어댑터 (ports 구현)
    │   ├── __init__.py
    │   ├── creon/
    │   │   ├── __init__.py
    │   │   ├── gateway_client.py       # creon-gateway HTTP 클라이언트
    │   │   ├── live_router.py          # OrderRouterPort 구현
    │   │   └── market_data_adapter.py  # MarketDataPort 구현
    │   ├── sim/
    │   │   ├── __init__.py
    │   │   ├── sim_router.py           # OrderRouterPort 구현
    │   │   └── sim_clock.py
    │   ├── fallback/
    │   │   └── naver_scraper.py        # 시세 백업 소스
    │   ├── notification/
    │   │   ├── email_adapter.py        # SMTP
    │   │   ├── telegram_adapter.py
    │   │   └── inapp_adapter.py
    │   ├── ml/
    │   │   ├── lstm_predictor.py       # MLModelPort 구현
    │   │   └── model_store.py          # 모델 파일 IO
    │   └── redis_pubsub.py             # 본체 ↔ gateway 통신
    │
    ├── workers/                # Celery Task 정의
    │   ├── __init__.py
    │   ├── tasks_signal.py             # 5초 주기 시그널 산출
    │   ├── tasks_order.py              # 주문/체결 처리
    │   ├── tasks_backtest.py           # 백테스트 작업
    │   ├── tasks_ml.py                 # 모델 재학습
    │   ├── tasks_notification.py       # 이메일/텔레그램
    │   └── tasks_market.py             # 시세 적재/배치
    │
    ├── scheduler/              # APScheduler 잡 정의
    │   ├── __init__.py
    │   ├── jobs.py
    │   └── market_calendar.py
    │
    ├── ws/                     # WebSocket 매니저
    │   ├── __init__.py
    │   ├── manager.py                  # 연결 풀, 사용자별 broadcast
    │   ├── quote_channel.py
    │   ├── signal_channel.py
    │   └── notification_channel.py
    │
    └── utils/
        ├── retry.py
        ├── crypto.py                   # AES-256 GCM
        └── validators.py               # 종목코드, 호가단위 등
```

---

## 3. 계층별 책임 상세

### 3.1 `api/` — 프레젠테이션
- **역할**: HTTP 요청 수신, Pydantic 검증, 인증/인가, 서비스 호출, 응답 직렬화.
- **금지**: 비즈니스 로직, DB 직접 접근, 외부 시스템 직접 호출.
- **명명**: 도메인별 파일 1개(`orders.py` 등), 각 라우터는 `router = APIRouter(prefix="/orders", tags=["orders"])`.
- **예시**:

```python
# app/api/v1/orders.py
from fastapi import APIRouter, Depends, Header
from app.api.deps.auth import require_user
from app.api.deps.trade_mode import require_trade_mode
from app.services.order_service import OrderService
from app.schemas.order import OrderCreateIn, OrderOut, Response

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=Response[OrderOut], status_code=201)
async def create_order(
    payload: OrderCreateIn,
    idempotency_key: str = Header(alias="X-Idempotency-Key"),
    user = Depends(require_user),
    mode = Depends(require_trade_mode),
    svc: OrderService = Depends(),
):
    order = await svc.create(user.id, mode, payload, idempotency_key)
    return Response(success=True, data=OrderOut.from_entity(order))
```

### 3.2 `services/` — 애플리케이션 서비스 (유스케이스)
- **역할**: 트랜잭션 경계, 도메인 객체 조합, 포트 호출, 유스케이스 단위.
- **트랜잭션**: `UnitOfWork` 컨텍스트로 명시적 시작/커밋.
- **OrderService**: 모드별 라우터를 DI로 주입받아 분기.

```python
# app/services/order_service.py
class OrderService:
    def __init__(self, uow, sim_router, live_router, risk_guard):
        self.uow = uow
        self._sim = sim_router
        self._live = live_router
        self._risk = risk_guard

    async def create(self, user_id, mode, payload, idem_key):
        async with self.uow:
            await self._risk.check(user_id, payload)
            order = Order.create(user_id, payload, mode)
            router = self._sim if mode == TradeMode.SIM else self._live
            result = await router.submit(order)
            await self.uow.orders.save(order, result)
            await self.uow.commit()
            return order
```

### 3.3 `domains/` — 도메인 계층
- **역할**: 순수 비즈니스 로직. 외부 의존 없음, 테스트 용이.
- **엔티티 vs 모델**: ORM Model은 `models/`, 도메인 엔티티는 `domains/entities/`에 분리.
- **포트**: 외부 시스템 인터페이스는 도메인에서 정의, 구현은 `integrations/`.

### 3.4 `repositories/` — 영속성 계층
- **역할**: SQLAlchemy 쿼리, 매핑(Model ↔ Entity).
- **인터페이스 분리**: 서비스는 Protocol 타입으로 의존, 구현체는 DI 컨테이너에서 주입.
- **금지**: 비즈니스 로직, 트랜잭션 시작/커밋 (UnitOfWork가 담당).

### 3.5 `integrations/` — 외부 통합
- **역할**: 도메인 포트의 구현체. HTTP 클라이언트, COM, SMTP 등.
- **재시도/타임아웃**: 어댑터 내부에서 처리 (`tenacity`).
- **테스트**: 단위 테스트는 모킹, 통합 테스트는 별도 마커.

### 3.6 `workers/` — Celery Task
- **역할**: 비동기 작업 진입점. 실제 로직은 `services`에 위임.
- **명명**: `tasks_<domain>.py`, 함수명은 `run_<action>`.

```python
# app/workers/tasks_signal.py
from app.celery_app import celery_app
from app.services.signal_service import SignalService

@celery_app.task(name="signal.evaluate", bind=True, max_retries=3)
def evaluate_signals(self, user_id: str):
    try:
        with container.scope() as scope:
            svc: SignalService = scope.resolve(SignalService)
            svc.evaluate_for_user(user_id)
    except TransientError as e:
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
```

### 3.7 `scheduler/` — APScheduler
- **역할**: 시간 기반 트리거(장 시작/종료, 야간 배치).
- **트리거 종류**: cron, interval.

| 잡 | 주기 | 액션 |
|---|---|---|
| `pre_market_warmup` | 평일 08:30 | 시세 캐시 워밍업, 모델 로딩 |
| `signal_pulse` | 평일 09:00~15:20, 5초 | Celery `signal.evaluate` enqueue |
| `cancel_stale_orders` | 평일 15:25 | 미체결 주문 일괄 취소 |
| `daily_report` | 평일 15:35 | 리스크 리포트 생성 + 메일 |
| `ml_retrain` | 평일 18:00 | 전 종목 LSTM 재학습 |
| `master_refresh` | 매일 06:00 | 종목/섹터/캘린더 갱신 |

### 3.8 `ws/` — WebSocket
- **역할**: 실시간 채널. Redis Pub/Sub 구독 → 사용자별 broadcast.
- **인증**: JWT를 쿼리 파라미터 또는 first message로 전달.

---

## 4. 의존성 주입 (DI)

- `dependency-injector` 패키지로 컨테이너 구성.
- FastAPI `Depends`는 컨테이너의 provider를 wrap.
- 서비스 → 리포지토리 → DB 세션 순으로 스코프 관리.

```python
# app/core/container.py
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    db = providers.Resource(init_db, dsn=config.DATABASE_URL)
    uow = providers.Factory(UnitOfWork, session_factory=db.provided.session_factory)
    sim_router = providers.Factory(SimRouter)
    live_router = providers.Factory(LiveRouter, client=providers.Factory(GatewayClient))
    risk_guard = providers.Factory(RiskGuard, uow=uow)
    order_service = providers.Factory(OrderService, uow=uow, sim_router=sim_router,
                                       live_router=live_router, risk_guard=risk_guard)
```

---

## 5. 설정 / 환경변수

- `app/core/config.py`에서 `pydantic.BaseSettings`로 일원화.
- `.env`는 `.env.example` 참조 (저장소 미포함).
- 카테고리: `APP_*`, `DB_*`, `REDIS_*`, `JWT_*`, `CREON_*`, `SMTP_*`, `LOG_*`.

---

## 6. 마이그레이션 (Alembic)

- 명명: `YYYYMMDDHHMM_<change>.py`.
- 정책: down_revision 필수, autogenerate 후 수동 검수.
- 시드 데이터: `alembic/seeds/` 별도 SQL 스크립트.

---

## 7. 테스트 전략

| 레벨 | 위치 | 도구 |
|---|---|---|
| Unit | `tests/unit/` | pytest, 도메인/지표/DSL 평가 |
| Integration | `tests/integration/` | pytest + testcontainers (Postgres/Redis) |
| E2E | `tests/e2e/` | pytest + httpx, 시나리오 단위 |
| Load | `tests/load/` | locust (선택, QA 협의) |

- 커버리지 목표: 도메인 80% / 서비스 70% / 전체 60% (코드 표준 §6 참조).
- `pytest-asyncio` 사용, `pytest -m "not slow"`로 빠른 피드백.

---

## 8. 코드 예시: 도메인 → 서비스 → API 흐름

```python
# domains/entities/order.py
@dataclass
class Order:
    id: UUID
    user_id: UUID
    code: str
    side: Side
    qty: int
    price: Decimal | None
    mode: TradeMode
    status: OrderStatus
    @classmethod
    def create(cls, user_id, payload, mode): ...

# domains/ports/order_router.py
class OrderRouterPort(Protocol):
    async def submit(self, order: Order) -> OrderResult: ...

# integrations/creon/live_router.py
class LiveRouter:
    def __init__(self, client: GatewayClient): self._c = client
    async def submit(self, order):
        resp = await self._c.post_order(order.to_dict())
        return OrderResult.from_response(resp)

# services/order_service.py 위 §3.2 참고

# api/v1/orders.py 위 §3.1 참고
```

---

## 9. 패키지 의존성 (pyproject 요지)

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110"
uvicorn = {extras = ["standard"], version = "^0.29"}
pydantic = "^2.6"
pydantic-settings = "^2.2"
sqlalchemy = "^2.0"
alembic = "^1.13"
asyncpg = "^0.29"
redis = "^5.0"
celery = "^5.3"
apscheduler = "^3.10"
dependency-injector = "^4.41"
httpx = "^0.27"
tenacity = "^8.2"
bcrypt = "^4.1"
python-jose = "^3.3"
loguru = "^0.7"
numpy = "^1.26"
pandas = "^2.2"
scikit-learn = "^1.4"
tensorflow = "^2.15"   # LSTM
```

---

## 10. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DevLead | 최초 작성 |
