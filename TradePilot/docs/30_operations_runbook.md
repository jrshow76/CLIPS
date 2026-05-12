# TradePilot 운영 런북

> 문서 ID: 30_OPERATIONS_RUNBOOK
> 버전: v1.0
> 작성자: BackendSenior
> 검토자: DevLead, PM, QA
> 최종 수정일: 2026-05-12

본 문서는 TradePilot 운영 담당자(BackendSenior / DevLead / 사용자 본인)가 매일 따라야 하는 일일 절차, 비상 상황 대응 방법, 시스템 재기동 절차, 데이터 정합성 점검 쿼리를 정의한다.

본 런북은 **모의투자(SIM) 운영부터 실거래(LIVE) 운영까지 동일하게 적용**되며, LIVE 모드일 때 추가 절차(빨간색 표시)를 따른다.

---

## 1. 일일 운영 절차 (장 시작 30분 전 ~ 마감 후)

### 1.1 타임라인

| 시각(KST) | 작업 | 책임자 | 자동/수동 |
|---|---|---|---|
| 08:00 | Windows 호스트 자동 부팅 (작업스케줄러) | 시스템 | 자동 |
| 08:00 ~ 08:05 | `start-gateway.ps1` 자동 실행 | 시스템 | 자동 |
| 08:05 ~ 08:15 | 일일 헬스 체크 (`scripts/daily_health_check.sh`) | BackendSenior | 자동 + 확인 |
| 08:15 ~ 08:25 | CREON 연결 / 시세 워밍업 확인 | BackendSenior | 수동 |
| 08:25 ~ 08:30 | 모델 / 전략 활성화 상태 점검 | 사용자 | 수동 |
| 08:30 | 자동매매 엔진 시작 (사전 점검 모드) | 시스템 | 자동 |
| 09:00 | 정규 매매 시작 (시그널/주문 활성) | 시스템 | 자동 |
| 09:00 ~ 15:20 | 모니터링 + 대시보드 확인 | BackendSenior, 사용자 | 수동 |
| 15:20 | 신규 매수 차단, 청산만 허용 | 시스템 | 자동 |
| 15:30 | 일일 정산 시작 | 시스템 | 자동 |
| 16:00 | 일일 리포트 생성 + 이메일 발송 | 시스템 | 자동 |
| 16:00 ~ 17:00 | 일일 리포트 검토 + 익일 운영 결정 | 사용자, PM | 수동 |
| 18:00 | ML 재학습 (옵션) | 시스템 | 자동 |

### 1.2 장 시작 전 체크리스트

```bash
# 1. 게이트웨이 헬스
curl -s http://gateway:9100/healthz | jq
curl -s http://gateway:9100/readyz | jq

# 2. 본체 헬스
curl -s http://backend:8000/api/v1/health | jq
curl -s http://backend:8000/api/v1/health/ready | jq

# 3. 자동 종합 점검
./scripts/daily_health_check.sh
```

**확인 항목** (모두 OK 이어야 09:00 정규 매매 진입):
- [ ] 게이트웨이 `/readyz` ok=true, com_connected=true
- [ ] 게이트웨이 trade_env가 의도한 값 (SIM 또는 LIVE)
- [ ] 본체 DB 연결 정상, Redis 연결 정상
- [ ] 마지막 일일 백업 < 24시간 전
- [ ] Celery 큐 적체 < 100건
- [ ] Redis 메모리 사용량 < 70%
- [ ] 디스크 여유 ≥ 20%
- [ ] CREON 시세 워밍업 (005930 quote 정상)
- [ ] Sentry/모니터링 경고 없음
- [ ] 운영자 본인 인앱 알림 수신 가능 (테스트 알림 발송)

### 1.3 장 종료 후 체크리스트

- [ ] `data_consistency_check.sql` 실행 (주문-체결 일치)
- [ ] 일일 리포트 수신 확인
- [ ] CRITICAL/ERROR 로그 라인 < 10건
- [ ] 미체결 주문 0건 (있다면 사유 확인)
- [ ] Kill Switch 작동 이력 확인
- [ ] DB 백업 작업 완료 (`pg_dump` 또는 백업 스크립트)

---

## 2. 비상 상황 대응

### 2.1 상황: CREON Plus 단절

**증상**: 게이트웨이 헬스비트 `com_connected=false`, 본체 LIVE→SIM 강제 전환 알림.

**자동 조치** (시스템):
1. 5초 주기 헬스 체크로 단절 감지
2. 최대 3회 자동 재연결 시도
3. 3회 실패 시 CRITICAL 알림 (`tp:gateway.alert`)
4. 본체에서 15초 이상 헬스비트 미수신 시 모든 LIVE 사용자 SIM 강제
5. 미체결 주문 일괄 취소

**수동 조치** (운영자):
1. Windows 호스트 원격 접속 (또는 직접 접근).
2. CREON Plus GUI 확인:
   - 로그인 상태? → 재로그인.
   - 매매 비밀번호 입력 상태? → 입력.
   - 인증서 만료? → 갱신.
3. CREON Plus 재기동 후 `start-gateway.ps1 -NoLogin` 으로 게이트웨이 재시작.
4. `GET /readyz` 로 복구 확인.
5. 본체 사용자 LIVE 복귀 안내 (Stage 4 운영 시).

**에스컬레이션**:
- 5분 내 복구 실패 → DevLead 호출.
- 30분 내 복구 실패 → PM 호출 + 사용자 통보.

### 2.2 상황: 게이트웨이 응답 지연

**증상**: `/orders` 응답 시간 > 5초 또는 타임아웃.

**확인**:
```bash
# 게이트웨이 메트릭
curl -s http://gateway:9100/metrics | grep request_count
curl -s -H "X-Gateway-Api-Key: $KEY" http://gateway:9100/system/status | jq
```

**원인별 대처**:
| 원인 | 조치 |
|---|---|
| `request_count_1s` 가 한도(12)에 근접 | RPS 조정 또는 본체 발주 페이싱 강화 |
| CREON 자체 지연 (시장 변동성↑) | 정상. 슬리피지 알림 강화 |
| Windows 호스트 CPU/메모리 포화 | 호스트 점검, 불필요 프로세스 종료 |
| 네트워크 RTT 증가 | VPN/네트워크 점검 |

### 2.3 상황: 주문 실패 폭증

**증상**: 1분 내 주문 실패율 > 5%.

**자동 조치**:
- Risk Guard 가 5% 초과 감지 → 신규 주문 일시 중지 (`order_router.blocked=true`).
- 인앱 + 이메일 알림 발송.

**수동 조치**:
1. 실패 사유 분석:
   ```sql
   SELECT error_code, COUNT(*) FROM orders 
   WHERE created_at > NOW() - INTERVAL '10 minutes' 
     AND status = 'REJECTED' 
   GROUP BY error_code 
   ORDER BY 2 DESC;
   ```
2. 사유별 대처:
   - E0011 (잔고 부족) 다수 → 사용자 한도 설정 점검.
   - E0027 (상하한가) 다수 → 시장 단위 차단 정책 발동.
   - E0028 (거래정지) → 종목 마스터 업데이트 필요.
3. Risk Guard 차단 해제: `POST /api/v1/admin/order-router/unblock` (관리자).

### 2.4 상황: 한도 초과 알림

**증상**: 사용자에게 "일일 매수 한도 도달" 알림.

**대처**: 정상 동작. 사용자가 한도를 조정하거나 익일 대기.

### 2.5 상황: Kill Switch 발동

**자동 조치** (5초 SLA):
1. `order_router.blocked=true` 즉시
2. 미체결 주문 일괄 취소
3. 자동매매 OFF
4. 인앱/이메일 알림
5. audit_log 1건 기록

**수동 조치**:
1. 발동 사유 확인 (`audit_log` 의 `kill_switch_reason`).
2. 사용자 안내.
3. 사유 해소 후 재활성화 (사용자 본인 명시적 액션 필요).

### 2.6 상황: 데이터베이스 다운

**증상**: 본체 API 5xx, DB 연결 실패 로그.

**자동 조치**:
- 자동매매 즉시 정지 (Kill Switch 발동).
- 게이트웨이는 계속 동작 (DB 없어도 주문/시세 가능).

**수동 조치**:
1. DB 컨테이너/프로세스 상태 확인.
2. 디스크 / 메모리 / Lock 확인.
3. PITR(시점 복구) 또는 가장 가까운 백업으로 복구.
4. 복구 후 데이터 정합성 점검 (`data_consistency_check.sql`).
5. PM 보고 + 운영 재개 결정.

---

## 3. 장애 에스컬레이션 트리

```
사고 발생
    ↓
운영자 1차 대응 (5분)
    ↓ 미해결
DevLead 호출 (15분 SLA)
    ↓ 미해결
PM 호출 (30분 SLA)
    ↓
사용자 통보 + 외부 커뮤니케이션
    ↓
RCA 작성 (24시간 내)
    ↓
재발 방지 계획 수립 (1주 내)
```

| 우선순위 | 정의 | 1차 대응 SLA |
|---|---|---|
| **P0 (Critical)** | 거래 중단, 데이터 손실 위험, 금전 손실 | 즉시 (5분 내 알림) |
| **P1 (High)** | 기능 일부 장애, 일시적 운영 차질 | 30분 |
| **P2 (Medium)** | 비기능 영향, 차주 fix 가능 | 1영업일 |
| **P3 (Low)** | 개선 사항 | 다음 릴리즈 |

---

## 4. 시스템 재기동 절차

### 4.1 게이트웨이만 재기동

```powershell
# Windows
Get-ScheduledTask -TaskName TradePilotCreonGateway | Stop-ScheduledTask
Get-Process python | Where-Object {$_.Path -like "*tradepilot*"} | Stop-Process
.\start-gateway.ps1
```

### 4.2 본체만 재기동

```bash
# Linux (Docker Compose)
docker compose restart backend worker scheduler
docker compose logs -f backend
```

### 4.3 전체 재기동 (긴급)

```bash
# 1. 자동매매 모든 사용자 OFF
psql -c "UPDATE users SET auto_trade_enabled=false;"

# 2. 미체결 주문 일괄 취소 (관리자 API)
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
     http://backend:8000/api/v1/admin/orders/cancel-all

# 3. 게이트웨이 재기동 (Windows)
# (4.1 참조)

# 4. 본체 재기동 (Linux)
docker compose down
docker compose up -d

# 5. 헬스 확인
./scripts/daily_health_check.sh

# 6. 사용자 안내
```

---

## 5. 데이터 정합성 점검 (SQL)

`scripts/data_consistency_check.sql` 를 매일 16:30 자동 실행하며, 결과는 PM/DevLead에게 이메일.

### 5.1 주문-체결 1:N 일치

```sql
-- 체결 합계 != 주문 수량인 주문 찾기
SELECT o.id, o.stock_code, o.qty AS order_qty, 
       COALESCE(SUM(e.qty), 0) AS executed_qty,
       o.status
  FROM orders o
  LEFT JOIN executions e ON e.order_id = o.id
 WHERE o.created_at::date = CURRENT_DATE
   AND o.status IN ('FILLED', 'PARTIALLY_FILLED')
 GROUP BY o.id, o.stock_code, o.qty, o.status
HAVING o.qty < COALESCE(SUM(e.qty), 0)        -- 과체결
    OR (o.status = 'FILLED' AND COALESCE(SUM(e.qty), 0) <> o.qty);
```

### 5.2 게이트웨이 발주수 vs DB 주문수

```sql
-- 일자별 LIVE 주문 수 (DB)
SELECT created_at::date AS d, COUNT(*) AS live_orders
  FROM orders
 WHERE trade_mode = 'LIVE'
   AND created_at::date >= CURRENT_DATE - 7
 GROUP BY 1 ORDER BY 1;

-- 게이트웨이 발주 로그와 비교 (audit_log)
SELECT created_at::date AS d, COUNT(*)
  FROM audit_log
 WHERE action = 'gateway_order_submit'
   AND created_at::date >= CURRENT_DATE - 7
 GROUP BY 1 ORDER BY 1;
```

두 결과가 일치해야 함.

### 5.3 일일 PnL 합계 일치

```sql
-- 일일 PnL: 체결 기반 vs 포지션 평가 기반
WITH realized AS (
  SELECT user_id, 
         SUM(CASE WHEN side='SELL' THEN qty*price ELSE -qty*price END) 
           - SUM(fee + tax) AS realized_pnl
    FROM executions
   WHERE ts::date = CURRENT_DATE
   GROUP BY user_id
), eval AS (
  SELECT user_id, SUM(eval_pnl) AS unrealized_pnl
    FROM positions
   WHERE updated_at::date = CURRENT_DATE
   GROUP BY user_id
)
SELECT u.email, 
       r.realized_pnl, 
       e.unrealized_pnl, 
       d.daily_pnl AS reported_pnl,
       (r.realized_pnl + COALESCE(e.unrealized_pnl, 0)) - d.daily_pnl AS diff
  FROM users u
  LEFT JOIN realized r ON r.user_id = u.id
  LEFT JOIN eval e ON e.user_id = u.id
  LEFT JOIN daily_pnl d ON d.user_id = u.id AND d.date = CURRENT_DATE
 WHERE ABS((r.realized_pnl + COALESCE(e.unrealized_pnl, 0)) - d.daily_pnl) > 1.0;
```

`diff` 가 1원 초과면 정합성 문제 → 즉시 RCA.

### 5.4 모드 일관성

```sql
-- LIVE 모드인데 SIM 주문이 있거나, SIM 모드인데 LIVE 주문이 있는 경우
SELECT u.id, u.email, u.trade_mode, o.trade_mode AS order_mode, COUNT(*)
  FROM users u
  JOIN orders o ON o.user_id = u.id
 WHERE o.created_at::date = CURRENT_DATE
   AND u.trade_mode <> o.trade_mode
 GROUP BY u.id, u.email, u.trade_mode, o.trade_mode;
```

결과 0건이어야 함.

### 5.5 미체결 잔여 점검

```sql
-- 장 종료 후 PENDING/PARTIALLY_FILLED 잔여
SELECT id, user_id, stock_code, qty, price, status, created_at
  FROM orders
 WHERE status IN ('PENDING', 'PARTIALLY_FILLED', 'ACCEPTED')
   AND created_at::date = CURRENT_DATE
 ORDER BY created_at;
```

장 종료 후 0건이 정상.

---

## 6. 백업 / 복구

### 6.1 백업 주기
| 대상 | 주기 | 보관 |
|---|---|---|
| PostgreSQL | 매일 16:30 (자동, pg_dump) | 30일 |
| Redis | 매시간 (RDB) | 7일 |
| 로그 파일 | 매일 (rotate) | 90일 |
| 게이트웨이 .env | 매주 (사용자 수동) | 영구 (안전한 위치) |

### 6.2 복구 리허설
- 월 1회 백업본을 staging 환경에서 복구 테스트.
- 복구 시간 측정 → SLA 30분 이내 목표.

---

## 7. 모니터링 대시보드 (참고)

- **게이트웨이**: `/metrics` (Prometheus) → Grafana 대시보드 "creon-gateway"
- **본체**: Sentry, FastAPI metrics, Celery Flower
- **사용자 대시보드**: 메인 화면 "운영 상태" 카드 (헬스비트 시각, trade_env, 미체결 수)

### 7.1 주요 알림 룰
| 룰 | 임계 | 채널 |
|---|---|---|
| 헬스비트 15초 미수신 | 1회 | 인앱 + 이메일 (HIGH) |
| 게이트웨이 단절 30초 | 1회 | 인앱 + 이메일 + SMS (CRITICAL) |
| 주문 실패율 5% | 1분간 | 인앱 + 이메일 |
| Redis 메모리 80% | 5분간 | 이메일 |
| 디스크 < 20% | 1회 | 이메일 |
| 일일 PnL 정합성 차이 | 1원 초과 | 이메일 |

---

## 8. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | BackendSenior | 최초 작성 |
