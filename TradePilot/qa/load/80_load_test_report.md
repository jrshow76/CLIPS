# TradePilot 부하 테스트 결과 보고서

> 문서 ID: 80_LOAD_TEST_REPORT
> 버전: v1.0
> 작성자: QA
> 검토자: DevLead, BackendSenior, DBA, PM
> 최종 수정일: 2026-05-14

---

## 0. 실행 요약 (Executive Summary)

| 항목 | 값 |
|---|---|
| 실행 방식 | **옵션 B (정적 분석 + 부하 모델링)** |
| 실행 일자 | 2026-05-14 |
| 실제 부하 측정 가능 여부 | 불가 (사유: 본 환경 docker 데몬 미가동, k6 미설치, SUT 부재) |
| 시나리오 수 | 5건 (`orders`, `signals`, `ws`, `mixed`, `backtest`) |
| 산출물 | 시나리오 k6 스크립트, 일괄 실행기, 분석기, 본 보고서, 튜닝 권장사항, SLA 정의 |
| 핵심 권장 | DB 풀 20→40, Redis 캐시 4종 추가, uvicorn workers 4→6, nginx zn_order 3→8 |

> 본 보고서의 수치는 **본 환경에서 k6 실행이 불가**했기 때문에, 코드/설정/리소스 한도에 기반한 **이론적 부하 모델링**으로 산출했다. 실제 staging에서 `qa/load/run_all_loads.sh` 실행 후 본 보고서의 "예상" 컬럼을 "측정" 컬럼으로 갱신해야 한다.

---

## 1. 실행 환경 명세

### 1.1 환경 확인 결과 (옵션 A 실패 사유)

```
$ docker compose ps
failed to connect to the docker API at unix:///var/run/docker.sock

$ which k6
(not found)

$ curl -s http://localhost:8000/healthz
(연결 거부, code=000)
```

본 환경(샌드박스)에서는 docker 데몬이 동작하지 않고, k6 바이너리도 설치되어 있지 않다. 또한 backend-api 컨테이너가 실행 중이지 않아 실제 부하 측정을 수행할 수 없다. 따라서 **옵션 B(정적 분석 + 모델링)** 로 진행한다.

### 1.2 가정한 부하 테스트 표준 환경

`docker-compose.prod.yml`의 리소스 제약을 기준으로 한다.

| 구성요소 | 한도 (cpus / mem) | k6 부하 모델링 기준 |
|---|---|---|
| nginx | 제한 없음 (호스트 영향) | worker_connections=4096 × auto |
| backend-api (uvicorn) | 2.0 vCPU / 2 GB | workers=4 (prod), 2 (dev) |
| backend-worker (celery) | 2.0 vCPU / 2 GB | concurrency=4 × 워커 수 |
| postgres (15-alpine) | 2.0 vCPU / 4 GB | 기본 max_connections=100 |
| redis (7-alpine) | 1.0 vCPU / 1 GB | maxmemory-policy=allkeys-lru |
| frontend (Next.js) | 1.0 vCPU / 1 GB | 정적 자산은 nginx 캐시 가정 |

### 1.3 nginx 부하 관련 설정 (현행)

| 항목 | 값 | 비고 |
|---|---|---|
| `worker_connections` | 4096 | events 블록 |
| `keepalive_timeout` | 65s | |
| `keepalive_requests` | 1000 | |
| `zn_api` (일반 API) | 10 r/s | per-IP |
| `zn_public` (비인증 GET) | 30 r/s | per-IP |
| `zn_order` (주문) | 3 r/s | per-IP, burst 별도 |
| `zn_ws` (WebSocket 핸드셰이크) | 20 r/s | per-IP |
| `zn_login` | 5 r/min | 브루트포스 방어 |
| `zn_conn` 동시 한도 | 100 conn/IP | |

> **중요**: Rate Limit은 **per-IP** 다. 부하 테스트 IP 1개로 100 RPS 주문을 보내면 `zn_order=3r/s`에 의해 즉시 차단된다. k6 시나리오는 **staging nginx에서 zn_order 우회 IP 등록 또는 별도 internal 경로** 로 실행해야 한다.

---

## 2. 시나리오별 결과 (이론적 모델링)

### 2.1 시나리오 1: `orders` (주문 API 100 RPS, 5분)

#### 설정
- 스크립트: `qa/load/k6_orders_burst.js`
- 워밍업 30s → 100 RPS 도달 1m → 유지 3m → 정리 30s
- 페이로드: `{code, side, qty, order_type}` + `X-Idempotency-Key`
- 트래픽: `POST /api/v1/orders` (SIM 모드)

#### 부하 모델링 근거
- uvicorn workers=4, 워커당 평균 처리 시간 가정 200ms → 워커별 5 RPS, 총 20 RPS
- DB I/O: orders 테이블 INSERT 1회 + audit_log INSERT 1회 + idempotency 조회 1회 = 평균 30ms (인덱스 적중 가정)
- async I/O 활용으로 워커당 동시성 10 → **이론적 최대 ≈ 200 RPS** (CPU bound 진입 전)

#### 예상 결과 (P95 SLA 500ms 기준)

| 지표 | 예상 값 | SLA | 판정 |
|---|---:|---:|:---:|
| 총 요청 수 | ~28,000 (5분간) | — | — |
| 성공률 | 99.5% | >99% | PASS |
| P50 (ms) | 80 | — | — |
| P95 (ms) | 380 | <500 | PASS |
| P99 (ms) | 1,200 | <1500 | PASS |
| 평균 RPS | 95 | 100 | 거의 도달 |
| 5xx | 0 | 0 | PASS |

#### 관찰 예상 문제
- **nginx zn_order=3r/s 차단**: 동일 IP로 100 RPS 발사 시 429 응답 폭증. 사전에 IP whitelist 또는 zn_order 우회 location 필요.
- **idempotency 충돌**: `X-Idempotency-Key`는 uuid v4이므로 동시 충돌 가능성은 무시 가능.
- **DB orders 테이블 INSERT 락**: PRIMARY KEY 충돌은 없으나 `idx_orders_user_id_created_at` 인덱스 페이지 분할로 latency spike 가능.

---

### 2.2 시나리오 2: `signals` (시그널 조회 200 RPS, 5분)

#### 설정
- 스크립트: `qa/load/k6_signals_burst.js`
- 임의 status/strategy/page/size 조합 → 캐시 회피 동시 측정
- 트래픽: `GET /api/v1/signals?...`

#### 부하 모델링 근거
- 조회 엔드포인트, async, DB pool 활용 가정
- 캐시 미적용 가정 시 워커당 50 RPS × 4 워커 = 200 RPS 한계
- 캐시 적용 시 P50 < 50ms 가능

#### 예상 결과

| 지표 | 캐시 X | 캐시 적용 후 | SLA | 판정 (캐시 X) |
|---|---:|---:|---:|:---:|
| P50 (ms) | 60 | 20 | — | — |
| P95 (ms) | 280 | 90 | <300 | 위태 |
| P99 (ms) | 850 | 250 | <800 | **FAIL** |
| 실패율 | 0.3% | 0% | <1% | PASS |

#### 관찰 예상 문제
- **N+1 쿼리 의심**: signals → strategies → users 조인 → 캐시 미적용 시 N+1 우려.
- **page 깊을수록 OFFSET 비용 증가**: page=5, size=50 조합에서 P99 spike.
- DB 풀 포화 시 503 / 504 발생 가능.

---

### 2.3 시나리오 3: `ws` (WebSocket 1,000 동시 연결, 5분)

#### 설정
- 스크립트: `qa/load/k6_ws_burst.js`
- ramp-up 60s → 1000 VUs → 5분 유지 → 30s 정리
- 각 연결: subscribe(quote, orderbook) + 30s ping

#### 부하 모델링 근거
- nginx `worker_connections=4096`, 워커 자동 = 호스트 vCPU
- 일반적인 4코어 호스트 기준 nginx 동시 연결 ≈ 16,384 가능
- 백엔드: 1 연결당 메모리 ~50KB (asyncio + WS state) → 1000 연결 ≈ 50MB (여유)
- 핵심 병목: **CREON Gateway 시세 fan-out**과 Redis pub/sub 처리량

#### 예상 결과

| 지표 | 예상 값 | SLA | 판정 |
|---|---:|---:|:---:|
| 동시 연결 최대 | 1,000 | 1,000 | PASS |
| 연결 성공률 | 99.2% | >98% | PASS |
| 핸드셰이크 P95 (ms) | 800 | <1500 | PASS |
| 핸드셰이크 P99 (ms) | 2,400 | <3000 | PASS |
| 비정상 종료 | 3 | <10 | PASS |
| 메시지 처리량 | ~5,000 msg/s (10종목 × 500 msg/s × broadcast) | — | 모니터 필요 |

#### 관찰 예상 문제
- **zn_ws=20r/s 핸드셰이크 제한**: 1000 연결 / 60s = 16.7 conn/s 로 안전 범위. ramp-up 더 짧게 하면 429.
- **CREON Gateway 의존**: 게이트웨이 끊김 시 모든 WS 연결로 동시 알림 → backpressure 발생 가능.
- **Redis pub/sub 처리량**: 종목별 채널 fan-out 시 1000 subscriber × 10종목 × 1msg/s = 10,000 msg/s. Redis 1코어 한도 (단일 스레드 100K ops/s 수준)에서 무리 없음.

---

### 2.4 시나리오 4: `mixed` (혼합 워크로드 50 VU, 10분)

#### 설정
- 스크립트: `qa/load/k6_api_mixed.js`
- 흐름: 로그인 → 대시보드 → 차트 → 시그널 → 주문 → sleep
- 50 VU × 평균 세션 5초 = ~10 sessions/s = ~50 req/s (한 세션당 5요청)

#### 예상 결과 (시나리오별 SLA)

| 흐름 단계 | 예상 P95 (ms) | SLA | 판정 |
|---|---:|---:|:---:|
| 로그인 (bcrypt) | 350 | <600 | PASS |
| 대시보드 | 180 | <500 | PASS |
| 차트 | 600 | <700 | 위태 |
| 시그널 | 220 | <500 | PASS |
| 주문 | 380 | <500 | PASS |
| 전체 P95 | 620 | <800 | PASS |

#### 관찰 예상 문제
- **bcrypt CPU 부하**: 로그인 한 번당 100~200ms CPU. 50 VU 동시 로그인 시 워커 CPU 포화 잠재.
- **차트 API**: 일봉 1년 = ~250포인트 × OHLCV. 5년 요청 시 1250포인트 → JSON 직렬화 비용.

---

### 2.5 시나리오 5: `backtest` (동시 10건)

#### 설정
- 스크립트: `qa/load/k6_backtest_concurrent.js`
- 10개 VU × 1 iteration, 5년 일봉 단일 종목
- celery worker concurrency=4

#### 부하 모델링 근거
- celery worker concurrency=4 → 4건 병렬, 6건 대기
- 단일 백테스트 처리 시간 가정 20s (CPU bound)
- 큐 적체 최대 깊이 = 6
- 10건 전체 완료 = 4건(20s 병렬) + 4건(20s) + 2건(20s) = 60s + 큐 대기 오버헤드

#### 예상 결과

| 지표 | 예상 값 | SLA | 판정 |
|---|---:|---:|:---:|
| 제출 P95 (ms) | 500 | <2000 | PASS |
| 단일 완료 P50 (s) | 25 | — | — |
| 단일 완료 P95 (s) | 80 | <1800 | PASS |
| 동시 10건 전체 완료 (s) | ~90 | <1800 | PASS |
| 완료 성공률 | >95% | >90% | PASS |

#### 관찰 예상 문제
- **메모리 누수 잠재**: 백테스트는 종가 시계열을 메모리에 로드. 5년 × 1종목 = 1.25K row × 8 컬럼 × 8B = ~80KB. 10건 동시 = 800KB. 다종목 백테스트(예: 100종목) 시 80MB → 워커 메모리 한도(2GB) 미달.
- **DB 풀 점유**: 백테스트 결과 INSERT가 트랜잭션을 길게 잡으면 다른 API 영향. → 별도 DB 사용자/풀 분리 권장.

---

## 3. 병목 분석 (이론적)

### 3.1 후보 병목 우선순위

| 우선순위 | 병목 | 발현 시나리오 | 근거 |
|---|---|---|---|
| **B1 (High)** | DB connection pool 포화 | mixed 50VU, signals 200 RPS | 기본 풀 크기 20 가정 시 200 RPS × avg 50ms = 10 동시 사용. 풀 한계 80% 도달 시 큐잉 |
| **B2 (High)** | uvicorn 워커 부족 (CPU bound 단계) | mixed (bcrypt), 차트 직렬화 | workers=4, vCPU=2 한계 → bcrypt 다수 동시에 큐잉 |
| **B3 (Med)** | Redis 캐시 미적용 → DB 반복 조회 | signals 200 RPS | 시그널/지수/섹터 등은 변경 빈도 낮음. 캐시 시 90% latency 감축 가능 |
| **B4 (Med)** | nginx zn_order=3r/s (운영 정책) | orders 100 RPS (테스트 자체) | 단일 IP 부하 시 차단. 사용자 패턴은 영향 적음 |
| **B5 (Med)** | celery concurrency=4 (백테스트) | backtest 10건 동시 | 6건 큐 대기. concurrency 늘리거나 큐 분리 |
| **B6 (Low)** | WS broadcast fan-out (Redis pub/sub) | ws 1000 conn | 현재 부하 수준에서는 여유. 5000+ 연결 시 재검토 |
| **B7 (Low)** | nginx worker_connections | ws ramp-up | 4096 × auto worker → 호스트 4코어 기준 16K. 1000 연결은 안전 |

### 3.2 코드 핫스팟 추정 (정적 분석 기반)

| 핫스팟 | 영향 시나리오 | 권장 액션 |
|---|---|---|
| `auth.login` → bcrypt (cost=12) | mixed | bcrypt cost=10 다운 고려 / argon2 마이그레이션은 별도 |
| `signals.list` → ORM N+1 (strategy join) | signals | `selectinload(Signal.strategy)` 명시 |
| `chart.get` → JSON 직렬화 큰 페이로드 | mixed.chart | 응답 캐시 (Redis 60s) + Content-Encoding gzip 확인 |
| `orders.create` → idempotency Redis SETNX | orders | TTL 24h 적정성 검토. Redis 메모리 점유 |
| `backtest.run` → pandas 메모리 사용 | backtest | 종가만 로드 (lazy column select), Float32 사용 |

### 3.3 임계점(Saturation Point) 추정

| 지표 | 안정 (P95 SLA 통과) | 한계 (성공률 95%) | 손익분기 (5xx 발생) |
|---|---:|---:|---:|
| `orders` RPS | 100 | 180 | 250 |
| `signals` RPS (캐시 X) | 200 | 320 | 450 |
| `signals` RPS (캐시 O) | 800 | 1,500 | 2,500 |
| 동시 WS 연결 | 1,000 | 3,000 | 5,000 |
| 동시 백테스트 | 10 | 20 | 40 |
| 동시 로그인 (bcrypt) | 30 | 60 | 100 |

> 위 수치는 모델링 결과이며, 실제 staging 측정 후 ±50% 보정 필요.

---

## 4. 데이터 정합성 / 부하 후 검증 항목

부하 테스트 종료 후 `docs/30_operations_runbook.md` 5절의 `data_consistency_check.sql` 을 반드시 실행한다.

- [ ] 주문-체결 수량 일치 (5.1)
- [ ] LIVE/SIM 모드 일관성 (5.4)
- [ ] 미체결 잔여 0건 (5.5) — 테스트 종료 후
- [ ] `idempotency_keys` 테이블 행 수 모니터링 — 부하 후 누적량 확인
- [ ] `audit_log` 비정상 패턴 (kill_switch_reason='load_test') 없음

---

## 5. 실측 갱신 절차 (옵션 A 가능 환경)

본 환경에서 실측 불가했으므로, staging 환경 보유자가 다음을 수행해 본 보고서의 "예상" 컬럼을 "측정"으로 교체한다.

```bash
# 1) staging 환경 진입 후
cd /path/to/TradePilot

# 2) k6 설치 확인
k6 version

# 3) staging 토큰 발급 (SIM 사용자)
export BASE_URL=https://staging.internal
export TOKEN=$(curl -s -X POST $BASE_URL/api/v1/auth/login \
  -d '{"email":"loadtest@example.com","password":"..."}' \
  -H 'Content-Type: application/json' | jq -r .access_token)

# 4) 일괄 실행 (백테스트 제외)
SKIP_BACKTEST=1 bash qa/load/run_all_loads.sh

# 5) 결과 디렉토리
ls qa/load/reports/

# 6) 분석 보고서 자동 생성됨
cat qa/load/reports/<TIMESTAMP>_analysis.md
```

각 시나리오 종료 후 다음 지표를 함께 캡쳐한다.
- Grafana: backend CPU/메모리, postgres 연결 수, redis 메모리, nginx upstream 응답시간
- `docker stats` 로 컨테이너 리소스 사용량
- `pg_stat_statements` top 10 슬로우 쿼리
- Sentry: 부하 테스트 윈도우 동안 에러 발생 건수

---

## 6. 결론 및 다음 단계

### 6.1 결론
- 본 환경에서 실측은 불가했으나, k6 시나리오 5종, 일괄 실행기, 분석기, SLA 정의를 모두 준비 완료.
- 정적 분석 결과 **DB 풀, uvicorn 워커, Redis 캐시 부재**가 주된 병목 후보.
- SLA 5종(API, WS, 매매, 백테스트, ML) 정의 완료 → `82_sla_definition.md` 참조.

### 6.2 다음 단계 (Owner)
| # | 액션 | 책임 | 기한 |
|---|---|---|---|
| 1 | staging 환경에서 `run_all_loads.sh` 실측 실행 | BackendSenior | D+3 |
| 2 | 본 보고서 "예상" → "측정" 갱신 | QA | D+5 |
| 3 | 튜닝 권장사항(P0) 적용 | DevLead + BackendSenior | D+7 |
| 4 | 튜닝 후 회귀 측정 + baseline 등록 | QA | D+10 |
| 5 | GitHub Actions nightly load 워크플로우 추가 | DevLead | D+14 |

---

## 7. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | QA | 옵션 B(정적 분석) 기반 최초 작성. 실측 갱신은 staging 환경 보유자가 수행 |
