# TradePilot DB 용량 계획 (Capacity Planning)

> 문서 ID: 92_CAPACITY_PLANNING
> 버전: v1.0
> 작성자: DBA
> 최종 수정일: 2026-05-14

본 문서는 TradePilot 데이터베이스의 향후 데이터 증가 예상량,
디스크 용량 계획, 백업 시간 예상, 스케일 업/아웃 시점 가이드를 제공한다.

수치는 **정성/실험 기반 추정**이며, 운영 6개월 시점에 실측치로 보정한다.

---

## 1. 데이터 증가 예상

### 1.1 워크로드 모델 (재확인)

| 항목 | 값 |
|---|---|
| 활성 종목 (LISTED) | 2,700 |
| 영업일 / 년 | ~250 |
| 활성 사용자 (1년차) | 5,000 |
| 활성 사용자 (3년차) | 25,000 |
| 활성 사용자 (5년차) | 50,000 |
| 사용자당 1일 시그널 | 평균 10 |
| 사용자당 1일 주문 (자동매매 LIVE) | 평균 4 |
| 사용자당 1일 알림 | 평균 30 |

### 1.2 핵심 테이블 행수/용량 추정

| 테이블 | 1행 평균 크기 | 일 INSERT | 1년 누적 (행) | 5년 누적 (행) | 5년 누적 (GB, 인덱스 포함) |
|---|---|---|---|---|---|
| `tp_market.price_daily` | ~150 B | 2,700 | 675,000 | 3,375,000 | ~0.7 GB |
| `tp_market.price_minute` (1m) | ~120 B | 200×390=78,000 | 19,500,000 | (1m은 1년 보관) | ~3 GB/년 |
| `tp_market.price_minute` (5m) | ~120 B | 200×78=15,600 | 3,900,000 | 19,500,000 | ~3 GB |
| `tp_market.price_minute` (15m/30m) | ~120 B | 200×(26+13)=7,800 | 1,950,000 | 9,750,000 | ~1.5 GB |
| `tp_analysis.indicators_daily` | ~400 B | 2,700 | 675,000 | 3,375,000 | ~1.8 GB |
| `tp_analysis.recommendations` | ~400 B | ~300 | 75,000 | 375,000 | ~0.2 GB (1년 보관: 0.04 GB) |
| `tp_analysis.signals` (1년차) | ~500 B | 5,000×10=50,000 | 12,500,000 | (2년 보관) | ~14 GB (1년) |
| `tp_analysis.signals` (3년차) | ~500 B | 25,000×10=250,000 | 62,500,000 | (2년 보관) | ~70 GB |
| `tp_trade.orders` (1년차) | ~350 B | 5,000×4=20,000 | 5,000,000 | 25,000,000 | ~10 GB |
| `tp_trade.orders` (3년차) | ~350 B | 25,000×4=100,000 | 25,000,000 | 125,000,000 | ~50 GB |
| `tp_trade.orders` (5년차) | ~350 B | 50,000×4=200,000 | 50,000,000 | (10년 보관) | ~200 GB |
| `tp_trade.fills` (5년차) | ~250 B | 200,000×1.2=240,000 | 60,000,000 | (10년 보관) | ~170 GB |
| `tp_trade.positions` | ~250 B | (적재 아님, 갱신) | ~50,000 (활성 5만 × 종목 3) | ~150,000 | ~0.05 GB |
| `tp_trade.portfolios` (스냅샷) | ~200 B | 50,000×1=50,000 | 12,500,000 | (10년) | ~30 GB |
| `tp_trade.daily_pnl` | ~200 B | 50,000 | 12,500,000 | 62,500,000 | ~30 GB |
| `tp_notify.notifications` | ~600 B | 50,000×3=150,000 | 37,500,000 | (6개월 보관) | ~22 GB (6개월) |
| `tp_audit.audit_order_history` | ~400 B | 200,000×2=400,000 | 100,000,000 | (10년) | ~600 GB |
| `tp_user.audit_login` | ~300 B | 50,000×3=150,000 | 37,500,000 | (1년 보관) | ~22 GB |

### 1.3 합계 (인덱스 포함, 5년 누적, 5년차 사용자 50,000명 기준)

| 카테고리 | 5년 누적 |
|---|---|
| 시세(price_*) | ~10 GB |
| 분석(indicators, signals, recommendations, ml) | ~80 GB |
| 매매(orders, fills, positions, portfolios, daily_pnl) | ~480 GB |
| 알림(notifications, alert_rules) | ~25 GB (6개월 회전 고려) |
| 감사(audit_*) | ~650 GB |
| 사용자/세션 | ~5 GB |
| **합계** | **~1.25 TB** |

> WAL/임시파일/백업 미포함. 실제 디스크는 안전 마진 2배 확보 권장 → **2.5 TB**.

---

## 2. 디스크 용량 계획

### 2.1 연차별 디스크 사용 추이

| 시점 | 활성 사용자 | DB 사이즈 (예상) | 권장 볼륨 |
|---|---|---|---|
| 출시 (T+0) | 100 | 5 GB | 100 GB SSD |
| T+6개월 | 1,000 | 30 GB | 200 GB SSD |
| T+1년 | 5,000 | 120 GB | 500 GB SSD |
| T+2년 | 12,500 | 350 GB | 1 TB SSD |
| T+3년 | 25,000 | 700 GB | 2 TB SSD |
| T+5년 | 50,000 | 1.25 TB | 2.5 TB SSD + 콜드 스토리지 |

### 2.2 WAL / 임시 파일 / 백업 별도 예상

| 항목 | 사이즈 |
|---|---|
| WAL (활성, 24h 보관) | ~50 GB |
| 임시 파일(work_mem 초과) | ~20 GB |
| 일일 베이스 백업 | DB 사이즈 × 1.2 (압축률 80% 가정 시 0.6배) |
| WAL 아카이브(2주) | ~700 GB |

### 2.3 콜드 스토리지(아카이브) 정책

- 보관기간 초과 파티션 → S3/Parquet 변환 (압축률 ~10:1)
- 예시: `orders_y2016m01` (10년 후 detach) → Parquet (10MB) → S3
- 콜드 스토리지 5년 누적 추정: ~70 GB (감사 로그 + 만료 시세)

---

## 3. 백업 시간 예상

### 3.1 pg_basebackup (Streaming)

| DB 사이즈 | 예상 시간 (1 Gbps) | 예상 시간 (10 Gbps) |
|---|---|---|
| 100 GB | ~15분 | ~2분 |
| 500 GB | ~75분 | ~10분 |
| 1 TB | ~2.5시간 | ~20분 |
| 2 TB | ~5시간 | ~40분 |

### 3.2 pg_dump (논리)

`pg_dump` 는 단일 트랜잭션 스냅샷 → 대용량은 비권장. **PITR (pg_basebackup + WAL archive)** 권장.

### 3.3 복구 시간 목표 (RTO)

| 시나리오 | 목표 RTO |
|---|---|
| 단일 테이블 데이터 복구 | 1시간 |
| 전체 DB 복구 (PITR) | 4시간 |
| 디스크 장애 (Patroni Failover) | 30초 |
| 리전 장애 (수동 DR) | 24시간 |

### 3.4 RPO (데이터 손실 허용량)

- 동기 replication: 0초 (LIVE 매매 트랜잭션은 동기 권장)
- 비동기 replication: 30초 이내
- WAL 아카이브: 5분(아카이브 주기)

---

## 4. 스케일 업 / 아웃 시점 가이드

### 4.1 수직 확장 트리거 (Scale Up)

| 지표 | 임계값 | 액션 |
|---|---|---|
| CPU 평균 사용률 | > 70% (24h) | CPU 인스턴스 업 |
| 메모리 사용률 | > 80% | shared_buffers 증설 또는 RAM 업 |
| 디스크 사용률 | > 70% | 볼륨 확장 또는 파티션 archive |
| IOPS | 한도의 80% | 디스크 타입 업그레이드 (gp3→io2) |
| 슬로우 쿼리 비율 | > 1% (24h) | 인덱스 추가 + plan 검토 |

### 4.2 수평 확장 트리거 (Scale Out / Read Replica)

| 지표 | 임계값 | 액션 |
|---|---|---|
| Read QPS | > 5,000 | Read Replica 추가 |
| 분석 쿼리 비율 | > 30% | OLAP용 Read Replica 분리 |
| 대시보드 응답 P95 | > 1초 | MV + Replica 분리 |
| 동시 활성 사용자 | > 1,000 | PgBouncer 풀 증설 + Replica |

### 4.3 샤딩(Citus 등) 검토 시점

- 활성 사용자 > 100,000
- DB 사이즈 > 5 TB
- 단일 인스턴스 IOPS 한계 도달
- → user_id 기반 샤딩 권장. orders/fills/signals 분포.

### 4.4 PostgreSQL 버전 업그레이드 시점

- 메이저 버전 EOL 18개월 전 (예: PG15 EOL 시점 12~24개월 전)
- 신규 기능 도입 필요 시 (예: PG17의 SLRU 개선 등)
- 무중단 업그레이드 도구: `pg_upgrade`, `logical replication`

---

## 5. 모니터링 지표 (Capacity)

```sql
-- DB 사이즈
SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;

-- 스키마별
SELECT n.nspname,
       pg_size_pretty(SUM(pg_total_relation_size(c.oid))) AS size
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r','p')
   AND n.nspname LIKE 'tp_%'
 GROUP BY n.nspname
 ORDER BY SUM(pg_total_relation_size(c.oid)) DESC;

-- 테이블별 TOP 20
SELECT n.nspname || '.' || c.relname AS table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
       pg_size_pretty(pg_relation_size(c.oid))       AS table_size,
       pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid)) AS index_toast_size
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind = 'r'
   AND n.nspname LIKE 'tp_%'
 ORDER BY pg_total_relation_size(c.oid) DESC
 LIMIT 20;

-- 파티션 분포
SELECT * FROM tp_audit.v_partition_stats LIMIT 20;
```

---

## 6. 비용 추정 (참고)

### 6.1 AWS RDS PostgreSQL 가정

| 시점 | 인스턴스 | 스토리지 | 월 비용 (예상, US-East) |
|---|---|---|---|
| T+0 (출시) | db.r6g.large (2vCPU/16GB) | 100GB gp3 | ~$150 |
| T+1년 | db.r6g.xlarge (4vCPU/32GB) | 500GB gp3 | ~$400 |
| T+3년 | db.r6g.2xlarge (8vCPU/64GB) | 2TB io2 | ~$1,500 |
| T+5년 | db.r6g.4xlarge (16vCPU/128GB) + Replica | 2.5TB io2 | ~$4,000 |

> Patroni + EBS 자가 운영 시 50~70% 절감 가능. 인력 비용 별도.

---

## 7. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-14 | DBA | 최초 작성. 90/91 문서와 함께 도입 |
