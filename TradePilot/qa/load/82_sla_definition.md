# TradePilot SLA 정의

> 문서 ID: 82_SLA_DEFINITION
> 버전: v1.0
> 작성자: QA
> 검토자: PM, DevLead, BackendSenior
> 최종 수정일: 2026-05-14

본 문서는 TradePilot 서비스의 서비스 수준 목표(SLO) 및 사용자 약속 SLA를 정의하고, 측정 방법을 명시한다.

용어 정의:
- **SLI (Service Level Indicator)**: 실제 측정 지표
- **SLO (Service Level Objective)**: 내부 목표
- **SLA (Service Level Agreement)**: 사용자/계약 대상 약속 (SLO 보다 보수적)

---

## 0. 한눈에 보기

| 영역 | 지표 | SLO (내부) | SLA (대외) | 측정 방법 |
|---|---|---|---|---|
| API | P95 응답 시간 | < 300ms | < 500ms | Prometheus `http_request_duration_seconds_bucket` |
| API | P99 응답 시간 | < 1000ms | < 2000ms | 동상 |
| API | 가용성 | 99.9% | 99.5% | uptime kuma + nginx 5xx 카운트 |
| WebSocket | 메시지 지연 P95 | < 100ms | < 200ms | k6 ws_burst + 서버 timestamp diff |
| WebSocket | 연결 성공률 | 99% | 99% | `ws_connect_success` (k6) |
| 매매 | 주문 제출-체결 P95 | < 500ms | < 1000ms | `executions.executed_at - orders.created_at` |
| 매매 | Kill Switch 발동 | < 5초 | < 5초 | `audit_log` ts vs 트리거 ts |
| 백테스트 | 5년 일봉 1종목 | < 30초 | < 60초 | celery task duration |
| ML 추론 | 단건 예측 | < 200ms | < 500ms | FastAPI `/api/v1/ml/predict` latency |

---

## 1. API SLA

### 1.1 응답 시간

| 카테고리 | P50 | P95 (SLO) | P95 (SLA) | P99 (SLO) | P99 (SLA) |
|---|---:|---:|---:|---:|---:|
| 공개 GET (시세, 검색) | 50ms | 200ms | 300ms | 500ms | 800ms |
| 인증 GET (리스트) | 80ms | 250ms | 400ms | 700ms | 1500ms |
| 인증 GET (단건) | 60ms | 200ms | 300ms | 500ms | 1000ms |
| POST (주문) | 100ms | 300ms | 500ms | 800ms | 1500ms |
| POST (백테스트 제출, 비동기) | 200ms | 500ms | 1000ms | 1500ms | 3000ms |
| POST (로그인 - bcrypt) | 150ms | 400ms | 600ms | 800ms | 1500ms |

### 1.2 가용성

| 항목 | SLO | SLA |
|---|---:|---:|
| 월간 가용성 | 99.9% | 99.5% |
| 월간 허용 다운타임 | 43.2분 | 3.6시간 |
| 단일 장애 최대 허용 시간 | 15분 | 30분 |

### 1.3 측정 방법
- nginx access.log `request_time` 분포 → Promtail → Loki / 또는 Prometheus exporter.
- FastAPI `prometheus-fastapi-instrumentator` 가 `http_request_duration_seconds_bucket` 제공.
- 5xx 카운트: `nginx_http_response_total{status=~"5..", path!~"/metrics|/healthz"}`.
- uptime kuma 가 30초 간격으로 `/healthz` polling.

### 1.4 Prometheus 알림 규칙 예시
```yaml
groups:
- name: api_slo
  rules:
  - alert: APIHighP95Latency
    expr: |
      histogram_quantile(0.95,
        sum(rate(http_request_duration_seconds_bucket{job="backend-api"}[5m])) by (le)
      ) > 0.5
    for: 10m
    labels: { severity: warning }
    annotations:
      summary: "API P95 응답시간이 500ms 초과 (10분 지속)"

  - alert: APIHigh5xxRate
    expr: |
      sum(rate(nginx_http_response_total{status=~"5..",path!="/metrics"}[5m]))
      /
      sum(rate(nginx_http_response_total{path!="/metrics"}[5m]))
      > 0.005
    for: 5m
    labels: { severity: critical }
    annotations:
      summary: "5xx 비율 0.5% 초과 (5분 지속)"
```

---

## 2. WebSocket SLA

| 항목 | SLO | SLA | 측정 |
|---|---:|---:|---|
| 핸드셰이크 P95 | 800ms | 1500ms | k6 `ws_handshake_ms` |
| 핸드셰이크 P99 | 1500ms | 3000ms | 동상 |
| 연결 성공률 | 99% | 98% | `ws_connect_success` |
| 메시지 지연 P95 (서버→클라이언트) | 100ms | 200ms | 서버 발행 ts vs 클라이언트 수신 ts |
| 메시지 손실률 | 0.1% | 0.5% | 시퀀스 번호 누락 검사 |
| 동시 연결 한도 | 1,000 (SLO 보장) | — | k6 burst 검증 |
| 정상 종료 후 재연결 시간 | 5초 | 10초 | 클라이언트 측 측정 |

### 2.1 측정 메트릭 (Prometheus)
```
# 백엔드에서 노출 필요
ws_active_connections{stream="market"}        gauge
ws_message_sent_total{stream,channel}         counter
ws_handshake_duration_seconds_bucket          histogram
ws_unexpected_close_total{code}               counter
```

### 2.2 메시지 지연 측정 방법
서버는 발행 시 `server_ts` 를 payload 에 포함:
```json
{"type":"quote","code":"005930","price":75000,"server_ts":1715659200.123}
```
클라이언트(또는 k6 스크립트)는 `Date.now() - server_ts * 1000` 으로 지연 추출, Trend 메트릭 적재.

---

## 3. 매매 SLA

### 3.1 핵심 매매 지표

| 지표 | SLO | SLA | 측정 |
|---|---:|---:|---|
| 주문 제출-체결 P95 | 500ms | 1000ms | `executions.ts - orders.created_at` |
| 주문 제출-체결 P99 | 1500ms | 3000ms | 동상 |
| Kill Switch 발동 | < 5초 | < 5초 | `audit_log.created_at - trigger_event_ts` |
| 주문 실패율 (시스템 원인) | < 0.5% | < 1% | `orders.status=REJECTED AND error_code IN ('SYS_*')` |
| SIM/LIVE 모드 정합성 | 100% | 100% | `data_consistency_check.sql` 5.4 |
| 일일 PnL 정합성 (오차) | ≤ 1원 | ≤ 1원 | `data_consistency_check.sql` 5.3 |

### 3.2 Kill Switch SLA 측정
```sql
SELECT
  trigger_id,
  trigger_ts,
  audit_ts,
  EXTRACT(EPOCH FROM (audit_ts - trigger_ts)) AS killswitch_latency_sec
FROM (
  SELECT
    al.id AS trigger_id,
    al.created_at AS trigger_ts,
    (SELECT MIN(created_at) FROM audit_log
       WHERE action='kill_switch' AND created_at > al.created_at) AS audit_ts
  FROM audit_log al
  WHERE al.action='kill_switch_trigger'
) t
WHERE EXTRACT(EPOCH FROM (audit_ts - trigger_ts)) > 5;
```
결과가 1건이라도 있으면 SLA 위반 → P0 알림.

### 3.3 주문 제출-체결 SLA (게이트웨이 경유)
```sql
SELECT
  date_trunc('day', o.created_at) AS d,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (e.ts - o.created_at))) AS p50,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (e.ts - o.created_at))) AS p95,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (e.ts - o.created_at))) AS p99
FROM orders o
JOIN executions e ON e.order_id = o.id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '7 days'
  AND o.trade_mode = 'LIVE'
GROUP BY 1
ORDER BY 1 DESC;
```

---

## 4. 백테스트 SLA

| 시나리오 | SLO | SLA | 측정 |
|---|---:|---:|---|
| 5년 일봉 단일 종목 | 30초 | 60초 | celery task duration |
| 5년 일봉 10종목 (멀티) | 90초 | 180초 | 동상 |
| 1년 분봉 단일 종목 | 60초 | 120초 | 동상 |
| 동시 처리 한도 | 10건 | 5건 | concurrency 측정 |
| 작업 실패율 | < 1% | < 5% | task status=FAILURE 비율 |

### 4.1 측정 메트릭
```
backtest_task_duration_seconds_bucket{strategy,period}  histogram
backtest_task_failures_total{strategy,reason}            counter
celery_queue_length{queue="backtest"}                    gauge
```

### 4.2 알림 룰
- `histogram_quantile(0.95, ...) > 60` 5분 지속 → warning.
- `celery_queue_length{queue="backtest"} > 20` 10분 지속 → critical (큐 적체).

---

## 5. ML 추론 SLA

| 시나리오 | SLO | SLA | 측정 |
|---|---:|---:|---|
| 단건 예측 P95 | 150ms | 200ms | FastAPI latency |
| 단건 예측 P99 | 400ms | 500ms | 동상 |
| 배치 100건 예측 | 2초 | 5초 | 측정 |
| 모델 가용성 | 99.9% | 99.5% | 모델 미로드 시 503 |
| 추론 실패율 | < 0.1% | < 0.5% | 5xx 비율 |

### 5.1 측정 메트릭
```
ml_inference_duration_seconds_bucket{model,version}     histogram
ml_inference_total{model,version,status}                counter
ml_model_loaded{model,version}                          gauge
```

---

## 6. SLA 보고 주기 및 책임

| 보고서 | 주기 | 책임 | 수신자 |
|---|---|---|---|
| 일일 SLA 대시보드 | 매일 09:00 | BackendSenior | PM, DevLead |
| 주간 SLA 요약 | 매주 월요일 | QA | PM, 사용자 |
| 월간 SLO 회고 | 매월 1일 | DevLead | PM, 전체 팀 |
| SLA 위반 RCA | 위반 24h 내 | DevLead | PM (CC: PM-→사용자) |

---

## 7. 에러 버짓 (Error Budget)

가용성 SLA 99.5% 기준 월간 에러 버짓:
- 30일 × 24h × 60min × 0.005 = **216분/월**
- 1회 장애 30분 = 버짓 14% 소모
- 버짓 50% 소진 → feature freeze 권장
- 버짓 100% 소진 → 다음 달까지 신기능 배포 중단, 안정화 우선

---

## 8. 측정 인프라 체크리스트

배포 전 다음 항목이 모두 가동 중인지 확인:

- [ ] Prometheus + Grafana 대시보드 "TradePilot-SLO"
- [ ] FastAPI `prometheus-fastapi-instrumentator` 활성
- [ ] nginx VTS 모듈 또는 nginx-prometheus-exporter
- [ ] postgres `pg_stat_statements` 확장 + `postgres_exporter`
- [ ] redis-exporter (`redis_*` 메트릭)
- [ ] celery-exporter (Flower 또는 prometheus-celery)
- [ ] uptime kuma (`/healthz`, `/api/v1/health/ready` 모니터)
- [ ] Sentry 통합 (에러 추적)
- [ ] Alertmanager → Slack/이메일 라우팅

---

## 9. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | QA | 최초 작성 |
