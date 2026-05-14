# TradePilot 부하 테스트 기반 튜닝 권장사항

> 문서 ID: 81_TUNING_RECOMMENDATIONS
> 버전: v1.0
> 작성자: QA
> 검토자: DevLead, BackendSenior, DBA
> 최종 수정일: 2026-05-14

본 문서는 `80_load_test_report.md` 의 병목 분석을 바탕으로, 운영 안정성 및 성능 향상을 위해 적용을 권장하는 튜닝 사항을 우선순위(P0/P1/P2)별로 정리한다.

각 권장사항은 (가) **현재 상태**, (나) **권장 변경**, (다) **예상 효과**, (라) **적용 난이도**, (마) **검증 방법** 을 포함한다.

---

## 0. 한눈에 보기

| 우선순위 | 항목 | 카테고리 | 예상 효과 | 난이도 |
|:---:|---|---|---|:---:|
| **P0-1** | DB connection pool 크기 조정 | DB | signals/mixed P95 30% 단축 | 낮음 |
| **P0-2** | Redis 캐싱 (signals/sectors/chart) | Cache | signals P95 60% 단축 | 중간 |
| **P0-3** | uvicorn workers 4 → 6 (prod) | Backend | mixed P95 20% 단축 | 낮음 |
| **P0-4** | nginx `zn_order` 3→8 (per-user 기준 재산정) | nginx | 사용자별 주문 처리량 2.5배 | 낮음 |
| **P1-1** | Celery worker concurrency 4→8 (signals/orders 큐) | Worker | 큐 적체 50% 감소 | 낮음 |
| **P1-2** | bcrypt cost 12→10 또는 argon2 마이그레이션 | Backend | 로그인 P95 50% 단축 | 중간 |
| **P1-3** | DB 인덱스 추가 (orders, signals 조회) | DB | 페이지 깊은 조회 P95 60% 단축 | 중간 (DBA 협의) |
| **P1-4** | 정적 자산 CDN (CloudFront/Cloudflare) | Frontend | 첫 페이지 LCP 40% 단축 | 중간 |
| **P2-1** | nginx `worker_connections` 4096→8192 | nginx | WS 동시 5000+ 대응 | 낮음 |
| **P2-2** | celery 큐 분리 (backtest 전용 워커) | Worker | API 응답 안정성↑ | 중간 |
| **P2-3** | gunicorn → uvicorn 마이그레이션 검토 | Backend | 비동기 효율 ↑ (현행 uvicorn이면 N/A) | — |
| **P2-4** | PgBouncer 도입 (transaction pooling) | DB | 단기 burst 흡수 | 높음 (DBA 협의) |
| **P2-5** | nginx Brotli 활성화 | nginx | API JSON 응답 크기 20% 감소 | 중간 |

---

## P0. 즉시 적용 권장 (Critical, D+7 이내)

### P0-1. DB connection pool 크기 조정

**현재 상태**
- SQLAlchemy(asyncpg) 기본 풀 크기 = `pool_size=5, max_overflow=10` (가정, backend 코드 확인 필요)
- postgres `max_connections=100` (기본값)

**권장 변경**
```python
# backend/app/db/engine.py 예시
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # 5 → 20
    max_overflow=20,       # 10 → 20
    pool_timeout=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)
```
- 다중 워커(uvicorn workers=4 또는 6) 환경에서 워커×풀크기가 postgres `max_connections` 의 70% 를 넘지 않도록 조정 (예: 6 워커 × 40 = 240 → postgres `max_connections=300` 권장).

**예상 효과**
- signals/mixed 시나리오 P95 30% 단축 (풀 대기 시간 제거).
- 503/504 0건 보장.

**적용 난이도**: 낮음 (한 줄 변경 + postgres 설정 한 줄).

**검증 방법**
1. 변경 전: `SHOW max_connections;`, `SELECT count(*) FROM pg_stat_activity;`
2. 적용 후 `signals` 시나리오 200 RPS 재실측 → P95 < 200ms 도달 여부.
3. Grafana: `pg_stat_database.numbackends` 가 워커 풀의 80% 이하 유지 확인.

---

### P0-2. Redis 캐싱 (조회 엔드포인트)

**현재 상태**
- `signals`, `sectors`, `chart`, `recommendations` 등 변경 빈도 낮은 GET 엔드포인트가 매 요청 DB 조회.

**권장 변경**
Redis 캐싱 대상 (TTL 권장):

| 엔드포인트 | TTL | Key | 무효화 트리거 |
|---|---|---|---|
| `GET /api/v1/signals?...` | 30s | `cache:signals:{user_id}:{status}:{page}:{size}` | 시그널 생성/마감 시 user_id 단위 invalidate |
| `GET /api/v1/sectors/rank` | 5분 | `cache:sectors:rank:{period}` | 5분 TTL 자연 만료로 충분 |
| `GET /api/v1/sectors/heatmap` | 1분 | `cache:sectors:heatmap` | 1분 TTL |
| `GET /api/v1/chart/{code}?interval=D` | 60s | `cache:chart:{code}:{interval}` | 일봉은 장 중에도 60s 캐싱 허용 |
| `GET /api/v1/market/index/{idx}` | 5s | `cache:idx:{idx}` | 실시간 지수 5s 캐싱 |

코드 예시 (FastAPI):
```python
from app.cache import cached
@router.get("/signals")
@cached(prefix="signals", ttl=30, vary=("user_id", "status", "page", "size"))
async def list_signals(...):
    ...
```

**예상 효과**
- `signals` 시나리오 P95 280ms → 90ms (-68%).
- DB 부하 60% 감소.
- 캐시 적중률 목표 ≥ 70% (반복 사용자 패턴 기준).

**적용 난이도**: 중간 (decorator + invalidation 로직).

**검증 방법**
1. `redis-cli MONITOR | head -100` 로 GET/SET 패턴 확인.
2. `k6_signals_burst.js` 의 `signals_cache_hit_estimate` 카운터 (P<50ms 응답 비율) 가 70% 이상.
3. Grafana: `pg_stat_statements` 의 signals 쿼리 호출 수가 60% 이상 감소.

---

### P0-3. uvicorn workers 4 → 6 (prod)

**현재 상태**
- `docker-compose.prod.yml` backend-api: `--workers 4`, CPU 한도 2.0
- 워커당 0.5 vCPU = bcrypt(0.2s CPU) 처리 시 워커 점유율 증가.

**권장 변경**
```yaml
# docker-compose.prod.yml
backend-api:
  command:
    - uvicorn
    - app.main:app
    - --host
    - "0.0.0.0"
    - --port
    - "8000"
    - --workers
    - "6"        # 4 → 6
  deploy:
    resources:
      limits:
        cpus: "3.0"   # 2.0 → 3.0 (워커 증가에 맞춤)
        memory: 3G    # 2G → 3G
```

**예상 효과**
- mixed 시나리오 P95 20% 단축 (bcrypt 큐잉 해소).
- CPU 자원 여유 확보.

**적용 난이도**: 낮음.

**검증 방법**
1. `docker stats tp-backend-api` 로 vCPU 사용량 80% 미만 확인.
2. mixed 시나리오 재실측 → 로그인 P95 < 300ms.

---

### P0-4. nginx `zn_order` rate limit 재산정

**현재 상태**
- `zn_order` 3 r/s **per IP**.
- 동일 NAT 뒤 여러 사용자가 동시 주문 시 차단 가능.
- 부하 테스트 자체도 단일 IP에서 100 RPS 발사 → 즉시 429.

**권장 변경**
```nginx
# infra/nginx/nginx.conf
limit_req_zone $http_authorization zone=zn_order_user:10m rate=8r/s;
# 또는: $binary_remote_addr + 별도 conf.d 에서 staging IP whitelist
```

기존 `$binary_remote_addr` 기반 zone을 유지하되 `zn_order` 한도를 3→8 로 상향, 또는 **JWT 토큰(Authorization 헤더) 기반 per-user limit zone** 도입.

추가로 `conf.d/_security.conf` 에 **부하 테스트 IP whitelist**:
```nginx
geo $is_loadtest_ip {
    default 0;
    10.0.99.0/24 1;   # k6 운영 서브넷
}
map $is_loadtest_ip $limit_key_order {
    0 $binary_remote_addr;
    1 "";   # 빈 키 → rate limit 비활성
}
limit_req_zone $limit_key_order zone=zn_order:10m rate=8r/s;
```

**예상 효과**
- 사용자당 초당 8주문 허용 (일반 사용자 시나리오에 충분).
- 부하 테스트 시 staging IP 차단 해제.

**적용 난이도**: 낮음.

**검증 방법**
1. `nginx -t && nginx -s reload`
2. `qa/load/k6_orders_burst.js` 실행 → 429 발생 0건.
3. 실 사용자 burst (동일 사용자 1초 5주문) 시 정상 처리 확인.

---

## P1. 단기 적용 권장 (High, D+30 이내)

### P1-1. Celery worker concurrency 4 → 8 (signals/orders 큐)

**현재 상태**
- `docker-compose.yml` backend-worker: `--concurrency=4 -Q default,signals,orders,backtest,ml,notifications`
- 모든 큐를 동일 워커가 처리 → 백테스트 작업이 signals 처리를 막을 수 있음.

**권장 변경**
큐별 워커 분리 + concurrency 조정.

```yaml
backend-worker-fast:
  command:
    - celery
    - -A
    - app.celery_app
    - worker
    - --loglevel=INFO
    - --concurrency=8
    - -Q
    - default,signals,orders,notifications

backend-worker-heavy:
  command:
    - celery
    - -A
    - app.celery_app
    - worker
    - --loglevel=INFO
    - --concurrency=2     # 동시 백테스트 2건 제한
    - -Q
    - backtest,ml
  deploy:
    resources:
      limits:
        cpus: "4.0"
        memory: 4G        # 백테스트 메모리 여유
```

**예상 효과**
- signals 큐 적체 50% 감소.
- 백테스트가 일반 API 영향 차단.

**적용 난이도**: 낮음 (compose 추가).

**검증 방법**
1. `celery -A app.celery_app inspect active_queues`
2. Flower 대시보드에서 큐별 처리 시간 분리 확인.
3. 백테스트 실행 중에도 `signals` k6 결과 P95 변동 5% 이내.

---

### P1-2. bcrypt cost 다운 또는 argon2 마이그레이션

**현재 상태**
- bcrypt cost=12 가정 → 1회 hash ≈ 200ms CPU.
- 다수 동시 로그인 시 워커 CPU 포화.

**권장 변경**
- 단기: bcrypt cost 12 → 10 (1회 ≈ 60ms).
- 중기: argon2id 마이그레이션 (이중 검증 윈도우 유지 후 단일화).

**예상 효과**
- 로그인 P95 350ms → 180ms (-48%).
- 동시 로그인 한계 30 → 80.

**적용 난이도**: 중간 (사용자 비밀번호 점진적 재해시).

**검증 방법**
1. mixed 시나리오 재실측 → 로그인 P95 < 200ms.
2. 기존 사용자 로그인 호환성 회귀 테스트.

---

### P1-3. DB 인덱스 추가 (DBA 협업, C4 작업과 연동)

**현재 상태**
- `signals.list` 페이지 깊은 조회 시 OFFSET 비용 증가.
- `orders.list` 사용자별 정렬에서 인덱스 누락 의심.

**권장 변경** (DBA 와 협의)
```sql
-- 시그널 사용자별 status + 시간순 조회
CREATE INDEX CONCURRENTLY idx_signals_user_status_created_at
  ON signals(user_id, status, created_at DESC);

-- 주문 사용자별 시간순 조회
CREATE INDEX CONCURRENTLY idx_orders_user_id_created_at
  ON orders(user_id, created_at DESC);

-- audit_log 사용자별 조회
CREATE INDEX CONCURRENTLY idx_audit_log_user_action
  ON audit_log(user_id, action, created_at DESC);

-- idempotency_keys TTL 정리 (24h 이전 행 삭제 배치)
DELETE FROM idempotency_keys WHERE created_at < NOW() - INTERVAL '24 hours';
```

**예상 효과**
- 페이지 깊은 signals 조회 P95 60% 단축.
- audit_log 조회 (관리자 화면) 응답 안정화.

**적용 난이도**: 중간 (CREATE INDEX CONCURRENTLY, DBA 협의 필수).

**검증 방법**
1. `EXPLAIN ANALYZE` 실행 → Index Scan 적용 확인.
2. `pg_stat_statements` 의 해당 쿼리 mean_exec_time 50% 이상 감소.

---

### P1-4. 정적 자산 CDN

**현재 상태**
- Next.js 정적 자산 (`/_next/static/...`) 이 nginx 경유로 서빙.

**권장 변경**
- CloudFront (S3 오리진) 또는 Cloudflare 도입.
- nginx `_next/static/` → CDN 캐시 (Cache-Control: max-age=31536000, immutable).

**예상 효과**
- 첫 페이지 LCP 40% 단축.
- 글로벌 사용자(있을 경우) 응답 안정.

**적용 난이도**: 중간 (DNS, CDN 설정, CI 빌드 산출물 업로드).

**검증 방법**
1. Lighthouse / WebPageTest 로 LCP 측정.
2. nginx access.log 의 `/_next/static/` 비율 감소 확인.

---

## P2. 중기 적용 (Medium, D+90 이내)

### P2-1. nginx `worker_connections` 4096 → 8192
- WS 동시 5000+ 연결 시 대비. ulimit 호스트 nofile 동시 상향 필요(`worker_rlimit_nofile=131072`).
- 검증: ws 시나리오 5000 VU 실험.

### P2-2. Celery 백테스트 전용 워커 노드 분리
- P1-1 의 확장. 백테스트는 별도 호스트로 격리.
- 검증: 백테스트 실행 중 API P95 변동 0%.

### P2-3. gunicorn → uvicorn 마이그레이션 검토
- 현재 prod 는 이미 uvicorn workers 모드. gunicorn 도입은 그래스풀 셧다운 필요 시 검토.

### P2-4. PgBouncer 도입 (transaction pooling)
- DB connection burst 흡수.
- DBA 협의 필수. transaction mode 사용 시 prepared statement 제약 검토.
- 검증: 단기 burst 1000 RPS 5초 동안 503 발생 0.

### P2-5. nginx Brotli 활성화
- `nginx.conf` 의 brotli 모듈 활성화 (openresty 또는 ngx_brotli 빌드 이미지 필요).
- 검증: API JSON 응답 크기 20% 감소, gzip 대비 5% 추가 감축.

---

## 적용 우선순위 종합 권장

```
Week 1: P0-1 (DB pool) + P0-3 (workers) + P0-4 (nginx rate)
Week 2: P0-2 (Redis 캐싱) → 가장 큰 효과
Week 3: P1-1 (celery 큐 분리) + P1-3 (인덱스, DBA 협업)
Week 4: P1-2 (bcrypt) + P1-4 (CDN)
Month 2~3: P2-* 우선순위 재평가 후 적용
```

각 단계 적용 후 `qa/load/run_all_loads.sh` 재실행 → `analyze_results.py` 의 베이스라인 비교(±5%) 로 회귀 가드.

---

## 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | QA | 최초 작성 |
