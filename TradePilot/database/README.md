# TradePilot Database 셋업 가이드

> 대상: DBA, BackendSenior, DevLead, 운영자
> 본 디렉토리는 TradePilot PostgreSQL 데이터베이스의 설계 문서와 초기화 SQL을 포함한다.

---

## 1. 디렉토리 구조

```
database/
├── 30_erd.md                 ERD (도메인별 Mermaid)
├── 31_schema_overview.md     스키마 개요 / 테이블 카탈로그
├── 32_index_strategy.md      인덱스/파티셔닝/통계 전략
├── 33_data_retention.md      데이터 보관·아카이빙 정책
├── README.md                 본 가이드
└── init/                     초기화 SQL (실행 순서 prefix)
    ├── 01_extensions.sql              확장(pgcrypto/citext/pg_trgm 등)
    ├── 02_schemas.sql                 스키마/공통 트리거 함수
    ├── 10_user_domain.sql             tp_user 도메인 DDL
    ├── 11_market_domain.sql           tp_market 도메인 DDL
    ├── 12_analysis_domain.sql         tp_analysis 도메인 DDL
    ├── 13_trade_domain.sql            tp_trade 도메인 DDL
    ├── 14_backtest_domain.sql         tp_trade 백테스트 테이블
    ├── 15_notification_domain.sql     tp_notify + tp_audit 도메인 DDL
    ├── 20_indexes.sql                 인덱스 (B-tree/BRIN/GIN/Partial)
    ├── 21_partitioning.sql            월별 RANGE 파티션 초기 생성
    ├── 30_seed.sql                    시드 데이터(섹터/지수/데모 사용자)
    └── 99_grants.sql                  역할 및 권한
```

---

## 2. 빠른 실행 (Docker Compose)

본 가이드는 `docker-compose.yml`에 PostgreSQL 15 서비스가 정의된 환경을 가정한다.

### 2.1 컨테이너 기동

```bash
# 프로젝트 루트에서
docker compose up -d postgres
docker compose ps   # postgres가 healthy인지 확인
```

### 2.2 초기화 스크립트 실행 (순서 중요)

```bash
DB_USER=postgres
DB_NAME=tradepilot
CONT=tradepilot-postgres

# init 디렉토리 마운트가 안 되어있다면 컨테이너에 복사
docker cp database/init "$CONT":/tmp/init

# prefix 순서대로 실행
docker exec -i "$CONT" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 \
    -f /tmp/init/01_extensions.sql \
    -f /tmp/init/02_schemas.sql \
    -f /tmp/init/10_user_domain.sql \
    -f /tmp/init/11_market_domain.sql \
    -f /tmp/init/12_analysis_domain.sql \
    -f /tmp/init/13_trade_domain.sql \
    -f /tmp/init/14_backtest_domain.sql \
    -f /tmp/init/15_notification_domain.sql \
    -f /tmp/init/20_indexes.sql \
    -f /tmp/init/21_partitioning.sql \
    -f /tmp/init/30_seed.sql \
    -f /tmp/init/99_grants.sql
```

> 만약 `docker-entrypoint-initdb.d`로 자동 적용하려면 `database/init` 디렉토리를 컨테이너 해당 경로에 마운트한다. 다만 자동 적용은 **신규 볼륨일 때만** 동작한다.

### 2.3 적용 확인

```bash
docker exec -it "$CONT" psql -U "$DB_USER" -d "$DB_NAME" -c "\dn"
docker exec -it "$CONT" psql -U "$DB_USER" -d "$DB_NAME" -c "\dt tp_user.*"
docker exec -it "$CONT" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT table_schema, COUNT(*) AS table_count
  FROM information_schema.tables
 WHERE table_schema LIKE 'tp_%'
 GROUP BY table_schema
 ORDER BY 1;
"
```

기대 결과 (총 39 테이블):

| schema | tables |
|---|---:|
| tp_analysis | 5 |
| tp_audit | 4 |
| tp_market | 8 |
| tp_notify | 3 |
| tp_trade | 12 |
| tp_user | 7 |

---

## 3. Alembic과의 관계

본 SQL 파일은 **초기 부트스트랩(원샷 셋업) 및 검토용** 이다. 운영 중 스키마 변경은 백엔드 Python의 **Alembic**으로 관리한다.

### 3.1 책임 분리

| 작업 | 도구 | 비고 |
|---|---|---|
| 신규 환경 부트스트랩 | `database/init/*.sql` | DBA 검토 용이 |
| 운영 중 마이그레이션 | `backend/alembic/versions/*` | 백엔드 PR과 동기 |
| 모델 정의(SQLAlchemy) | `backend/app/models/*` | 코드 진실 |

### 3.2 동기화 방침

1. 초기 SQL과 Alembic 첫 리비전은 **동일 스키마**를 정의해야 한다.
2. 신규 DDL 변경 시:
   - BackendSenior가 Alembic 리비전을 생성(`alembic revision --autogenerate`).
   - 동일 변경을 본 디렉토리의 SQL 파일에도 반영(검토용).
   - DBA가 인덱스/통계 영향 검토 후 승인.
3. 충돌 시 **Alembic을 진실의 원천(SoT)** 으로 한다.

### 3.3 운영 적용 절차

```bash
# 신규 환경
docker compose up -d postgres
# init/*.sql 적용 (위 2.2 참고)
cd backend
alembic stamp head    # 초기 SQL이 head와 동일하다고 마킹

# 이후 변경
alembic upgrade head
```

---

## 4. 파티션 운영

### 4.1 자동 생성 (cron)

매월 25일 02:00 KST에 익월 파티션을 사전 생성한다.

```bash
# scripts/db/create_partition.sh (예시)
PSQL="docker exec -i tradepilot-postgres psql -U postgres -d tradepilot"

YEAR=$(date -d "+1 month" +%Y)
MONTH=$(date -d "+1 month" +%-m)

$PSQL <<SQL
SELECT public.fn_create_monthly_partition('tp_market', 'price_minute',        $YEAR, $MONTH);
SELECT public.fn_create_monthly_partition('tp_trade',  'orders',              $YEAR, $MONTH);
SELECT public.fn_create_monthly_partition('tp_trade',  'fills',               $YEAR, $MONTH);
SELECT public.fn_create_monthly_partition('tp_notify', 'notifications',       $YEAR, $MONTH);
SELECT public.fn_create_monthly_partition('tp_audit',  'audit_order_history', $YEAR, $MONTH);
SQL
```

### 4.2 오래된 파티션 아카이빙

```sql
-- 예: 2025-01-01 이전 분봉 파티션 분리
SELECT public.fn_detach_old_partition('tp_market', 'price_minute', '2025-01-01');
-- DETACH 후 Parquet export → S3 업로드 → DROP TABLE
```

상세 절차는 [`33_data_retention.md`](33_data_retention.md) 3절 참고.

---

## 5. 권한 모델 요약

| 역할 | 용도 | 권한 |
|---|---|---|
| `app_admin` | DDL/마이그레이션 | 전 스키마 ALL |
| `app_user` | 백엔드 API | DML on tp_user/trade/notify/analysis, SELECT on tp_market, INSERT on tp_audit |
| `app_worker` | 시세/지표/시그널 워커 | DML on tp_market/analysis, SELECT on tp_user/trade |
| `app_readonly` | 리포트/모니터링 | SELECT all (단, password_hash 제외) |

상세는 `init/99_grants.sql` 참고.

---

## 6. 백업/HA

상세는 [`33_data_retention.md`](33_data_retention.md) 4·5절 참고.

요약:
- 일 1회 `pg_basebackup` + WAL 아카이빙 → S3
- 주 1회 `pg_dump`
- Patroni + etcd로 자동 Failover
- RPO 5분 / RTO 30분

---

## 7. 트러블슈팅

### 7.1 외래키 충돌
`13_trade_domain.sql`은 `12_analysis_domain.sql` 이후 실행되어야 한다(signals.strategy_id FK 추가 단계 존재).

### 7.2 파티션 미존재 데이터
DEFAULT 파티션에 적재된 후 알람이 발생한다. `pg_stat_user_tables` 모니터링 + 신규 파티션 생성으로 해결.

### 7.3 권한 부족 (운영)
신규 테이블 추가 후 `app_user`가 SELECT 불가하면 `ALTER DEFAULT PRIVILEGES` 적용을 확인한다. 기존 테이블에는 별도 `GRANT` 필요.

---

## 8. 문서 매핑

| 산출물 | 경로 |
|---|---|
| ERD | `30_erd.md` |
| 스키마/카탈로그 | `31_schema_overview.md` |
| 인덱스/파티셔닝 | `32_index_strategy.md` |
| 보관·아카이빙 | `33_data_retention.md` |

---

## 9. 변경 이력
| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v1.0 | 2026-05-12 | DBA | 최초 작성 |
