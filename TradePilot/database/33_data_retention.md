# TradePilot 데이터 보관·아카이빙 정책

> 문서 ID: 33_DATA_RETENTION
> 버전: v1.0
> 작성자: DBA
> 최종 수정일: 2026-05-12

본 문서는 TradePilot 시스템의 데이터 보관 기간, 아카이빙 전략, 익명화 절차, 백업/복구 정책을 정의한다. 본 정책은 SRS의 비기능 요구사항 NFR-DATA-001~003을 충족한다.

---

## 1. 보관 기간 정책

### 1.1 법정/요구사항 기반 보관 기간

| 데이터 분류 | 보관 기간 | 근거 |
|---|---|---|
| 거래 내역 (`orders`, `fills`, `daily_pnl`, `portfolios`) | **10년** | NFR-DATA-002 (법정), 금융투자업감독규정 |
| 시세 일봉 (`price_daily`, `market_index_daily`) | **5년** | NFR-DATA-001 |
| 시세 분봉 1m (`price_minute` 1분) | **1년** | 원본은 1년, 이후 집계로 대체 |
| 시세 분봉 5m/15m/30m | **5년** | 백테스트 활용 |
| 지표 캐시 (`indicators_daily`) | **5년** | 시세와 동기 |
| 추천/시그널 (`recommendations`, `signals`) | **2년** | 성과 분석 |
| ML 예측 (`ml_predictions`) | **1년** | 정확도 모니터링 |
| 백테스트 잡/결과 (`backtest_runs`, `backtest_results`, `backtest_trades`) | **1년** (저장된 결과는 사용자 삭제 시까지) | - |
| 알림 (`notifications`) | **90일** (읽음 후 30일) | UX |
| 로그인 감사 (`audit_login`) | **1년** | 보안 |
| 거래 감사 (`audit_trade_mode`, `audit_order_history`, `audit_risk_event`, `audit_role_change`) | **10년** | NFR-SEC-004, 거래와 동기 |
| OTP (`otp_codes`) | **7일** | 보안 (단방향 해시) |
| 세션 (`sessions`) | 만료 후 **30일** | 보안 추적 |
| 사용자 정보 (`users`, `user_profiles`) | 영구(탈퇴 30일 후 익명화) | NFR-DATA-003 |

### 1.2 보관 기간 만료 시 조치

| 만료 데이터 | 조치 |
|---|---|
| 시세/지표 | 콜드 스토리지(S3 Parquet)로 export → 파티션 DROP |
| 거래/감사 (10년 만료) | 콜드 스토리지로 export + 무결성 해시(SHA-256) 기록 → 파티션 DROP |
| 알림/OTP/세션 | 직접 삭제 (`DELETE` 또는 파티션 DROP) |
| 백테스트 잡 | 결과 미저장 잡은 30일 후 삭제, 저장된 결과는 사용자가 삭제 |

---

## 2. 사용자 탈퇴 처리 (NFR-DATA-003)

### 2.1 탈퇴 절차

1. 사용자가 탈퇴 요청 → `users.deleted_at = now()` 마킹 (즉시 로그인 차단).
2. **30일 grace period** 동안 복구 가능 상태로 유지.
3. 31일 차에 익명화 배치 실행:
   - `users.email` → `deleted_<id>@anonymized.local`
   - `users.nickname` → `탈퇴회원_<id>`
   - `users.phone` → `NULL`
   - `users.password_hash` → 무효값 (`'!'`)
   - `user_profiles.avatar_url` → `NULL`
   - `user_profiles.extra` → `'{}'::jsonb`
   - 즐겨찾기/세션/OTP → 삭제
   - **거래 내역(orders, fills)은 보존** (법정 10년), 단 `user_id`는 유지하되 PII 컬럼만 익명화
4. 알림/시그널 등 사용자 종속 데이터는 즉시 삭제(CASCADE).

### 2.2 익명화 함수 (의사 코드)

```sql
CREATE OR REPLACE FUNCTION tp_user.anonymize_user(p_user_id BIGINT)
RETURNS void AS $$
BEGIN
  UPDATE tp_user.users
     SET email = 'deleted_' || id || '@anonymized.local',
         nickname = '탈퇴회원_' || id,
         phone = NULL,
         password_hash = '!',
         locked_until = '2999-12-31'::timestamptz,
         updated_at = now()
   WHERE id = p_user_id AND deleted_at IS NOT NULL;

  UPDATE tp_user.user_profiles
     SET avatar_url = NULL, extra = '{}'::jsonb, updated_at = now()
   WHERE user_id = p_user_id;

  DELETE FROM tp_user.sessions WHERE user_id = p_user_id;
  DELETE FROM tp_user.otp_codes WHERE user_id = p_user_id;
  DELETE FROM tp_user.user_favorites WHERE user_id = p_user_id;

  INSERT INTO tp_audit.audit_role_change(user_id, from_role, to_role, actor_user_id, reason)
  VALUES (p_user_id, NULL, 'ANONYMIZED', NULL, 'GDPR-30day grace period');
END;
$$ LANGUAGE plpgsql;
```

---

## 3. 아카이빙 전략

### 3.1 아카이브 대상

| 테이블 | 트리거 | 출력 형식 | 보관 위치 |
|---|---|---|---|
| `price_minute_yYYYYmMM` | 13개월 경과 (1분봉) | Parquet (Snappy 압축) | S3: `s3://tradepilot-archive/price_minute/year=YYYY/month=MM/` |
| `orders_yYYYYmMM` | 10년 경과 | Parquet + JSON 메타 | S3: `s3://tradepilot-archive/orders/...` |
| `fills_yYYYYmMM` | 10년 경과 | Parquet | S3 |
| `audit_order_history_yYYYYmMM` | 10년 경과 | Parquet + 무결성 해시 | S3 |

### 3.2 아카이빙 절차 (자동)

1. 매월 1일 02:00 cron 트리거.
2. 대상 파티션을 `DETACH PARTITION` (운영 영향 최소화).
3. `COPY (SELECT ...) TO STDOUT (FORMAT csv)` → Parquet 변환 (pandas/duckdb).
4. SHA-256 해시 산출 → 메타 파일에 기록.
5. S3 업로드 + 무결성 검증.
6. `DROP TABLE` (파티션 자식 테이블 삭제).
7. 결과를 `tp_audit.audit_archive_log`에 기록.

### 3.3 복원 절차

- 콜드 스토리지에서 Parquet 다운로드.
- 임시 외부 테이블(Foreign Data Wrapper or 임시 일반 테이블) 적재.
- 필요 시 `ATTACH PARTITION` 또는 별도 분석용 스키마로 임포트.

---

## 4. 백업 정책

### 4.1 백업 종류 및 주기

| 종류 | 도구 | 주기 | 보관 |
|---|---|---|---|
| 논리적 풀 백업 | `pg_dump` (--format=custom) | **주 1회**(일요일 03:00) | 4주 |
| 물리적 풀 백업 | `pg_basebackup` + WAL 아카이빙 | **일 1회**(03:00) | 14일 |
| WAL 아카이빙 | `archive_command` → S3 | 연속(write-ahead) | 14일 |
| 스냅샷(클라우드) | EBS 스냅샷 | **일 1회** | 7일 |

### 4.2 백업 검증

- **월 1회 복원 훈련**(non-prod 환경): 가장 최신 백업으로 신규 인스턴스 복원 → 데이터 카운트 검증.
- 백업 파일 SHA-256 해시 검증.
- 백업 누락 알람: 24시간 내 신규 백업 미존재 시 PM·DevLead·DBA에 알림.

### 4.3 RPO / RTO 목표

| 지표 | 목표 | 비고 |
|---|---|---|
| RPO (Recovery Point Objective) | **5분** | WAL 아카이빙 기반 PITR |
| RTO (Recovery Time Objective) | **30분** | 단일 노드 장애 (replica 승격) |
| RTO (재해복구) | **2시간** | 별도 리전 백업 복원 |

---

## 5. 고가용성(HA) 및 복제

### 5.1 구성

```
   Primary(Master) ── Streaming Replication ──> Standby(Hot Standby)
        │                                              │
        ├── WAL Archive ─> S3                          │
        │                                              │
       Patroni + etcd (자동 Failover)
```

- **Patroni + etcd**로 자동 Failover 관리.
- **Streaming Replication** (synchronous_commit = `remote_apply`로 무손실 옵션).
- Read Replica 1대 추가 운영: 리포트/분석 트래픽 분리.

### 5.2 Failover 절차

1. Patroni가 Primary 헬스체크 실패 감지(3회 연속).
2. 자동 승격 결정 → Standby가 Primary로 전환.
3. 애플리케이션 측 DNS/연결 풀(pgBouncer) 재연결.
4. 구 Primary 복구 시 → 자동 Re-init 후 Standby로 합류.
5. PM에 자동 알림 발송.

---

## 6. 데이터 정합성 검증

### 6.1 정기 검증 (배치)

| 검증 | 주기 | 방법 |
|---|---|---|
| 일봉 데이터 결측 | 일 1회 | 영업일별 종목 카운트 < 예상치 알람 |
| 분봉 데이터 결측 | 시 1회 | 종목별 마지막 ts 시간차 임계값 |
| 포지션 vs 체결 누적 정합 | 일 1회 | 종목별 누적 (BUY - SELL) qty = position.qty |
| 일일 손익(daily_pnl) 재계산 일치 | 일 1회 | 체결 기반 재집계와 일치 여부 |
| 감사 로그 누락 | 일 1회 | 주문 상태 변경 건수 = audit_order_history 건수 |

### 6.2 운영 알람

- 정합성 검증 실패 → Slack `#dba-alert` 채널 + 운영자 이메일.
- 24시간 내 미해결 시 PM에 에스컬레이션.

---

## 7. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DBA | 최초 작성 |
