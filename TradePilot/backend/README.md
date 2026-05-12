# TradePilot Backend

TradePilot 자동주식매매 시스템의 FastAPI 백엔드.

## 기술 스택

- **언어**: Python 3.11+
- **웹 프레임워크**: FastAPI 0.110, Uvicorn
- **DB**: PostgreSQL 15 (asyncpg + SQLAlchemy 2.x async)
- **마이그레이션**: Alembic (DDL은 `database/init/*.sql`에서 관리, Alembic은 더미 base)
- **메시지/캐시**: Redis 7 (캐시 + Celery 브로커 + Pub/Sub)
- **워커**: Celery 5 (5개 큐: `signals`, `orders`, `backtest`, `ml`, `notifications`)
- **스케줄러**: APScheduler
- **인증**: PyJWT(HS256), Passlib(bcrypt cost=12)
- **지표**: pandas-ta (TA-Lib 미사용)
- **로그**: structlog (JSON, trace_id 전파)
- **테스트**: pytest, pytest-asyncio
- **코드 스타일**: ruff + black (line=100)

## 디렉토리 구조

```
backend/
├── app/
│   ├── core/            # 설정/DB/Redis/보안/로깅/예외/응답/미들웨어
│   ├── api/v1/          # REST 라우터 (도메인별)
│   ├── api/deps/        # FastAPI Depends (인증/모드 가드)
│   ├── schemas/         # Pydantic v2 DTO
│   ├── services/        # 유스케이스 (트랜잭션 경계)
│   ├── domains/         # 도메인 계층 (엔티티/포트/룰/지표)
│   ├── repositories/    # DB 접근 (SQLAlchemy)
│   ├── models/          # ORM 모델 (DDL 1:1)
│   ├── integrations/    # 외부 통합 어댑터 (Creon, Sim, SMTP)
│   ├── workers/         # Celery 태스크
│   ├── scheduler/       # APScheduler 잡
│   └── main.py          # FastAPI 엔트리포인트
├── alembic/             # DB 마이그레이션 (init SQL이 베이스)
├── tests/               # unit / integration
├── pyproject.toml
└── Dockerfile
```

## 로컬 개발 셋업

### 1. 의존성 설치

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. 환경변수

```bash
cp ../.env.example ../.env
# .env에서 JWT_SECRET, AES_KEY 등을 설정
```

### 3. 인프라 기동

```bash
# 프로젝트 루트에서
docker compose up -d postgres redis
```

DDL은 PostgreSQL 컨테이너 최초 기동 시 `database/init/*.sql`로 자동 적용된다.

### 4. API 서버 실행

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Healthcheck: http://localhost:8000/healthz, /readyz

### 5. 워커 실행

```bash
celery -A app.celery_app worker --loglevel=INFO -Q default,signals,orders,backtest,ml,notifications
```

### 6. 테스트

```bash
pytest -m unit          # 빠른 단위 테스트
pytest -m integration   # DB/Redis 필요
pytest --cov=app        # 커버리지
```

## 개발 규약

- **응답 포맷**: `app.core.response.success_response()` / `error_response()` 사용
- **예외**: `app.core.exceptions.AppException` 상속, 코드 `Exxxx` 부여
- **인증**: `Depends(get_current_user)`
- **모드 가드**: `Depends(require_trade_mode)` (주문 API)
- **멱등성**: `X-Idempotency-Key` 헤더 처리 (Redis 24h)
- **로그**: `structlog.get_logger()` 사용, trace_id는 미들웨어가 자동 주입

## 도메인별 구현 책임

| 도메인 | 담당 |
|---|---|
| Auth, Orders, Indicator/Signal, SimRouter/LiveRouter, Celery 워커 | BackendSenior |
| Stocks/Sectors/Strategies/Backtest/Portfolios/Notifications/Settings 등 CRUD | BackendDev |

신규 CRUD 도메인 추가 시 다음 순서를 따른다:
1. `models/<domain>.py` 추가 (DDL과 1:1)
2. `repositories/<domain>_repository.py` 추가 (BaseRepository 상속)
3. `schemas/<domain>.py` 추가 (Pydantic v2)
4. `services/<domain>_service.py` 추가 (유스케이스)
5. `api/v1/<domain>.py` 추가 (라우터, `success_response` 사용)
6. `api/v1/__init__.py`에 라우터 등록

## 참고 문서

- `docs/20_architecture.md` - 시스템 아키텍처
- `docs/21_backend_structure.md` - 백엔드 구조 상세
- `docs/24_api_response_spec.md` - API 응답 규약
- `docs/14_exception_policy.md` - 에러 코드 체계
- `docs/15_trading_policy.md` - 매매 정책
