# 데이터 볼륨 추정 & 용량 계획 (Data Volume & Capacity Planning)

| 항목 | 내용 |
|---|---|
| 문서명 | 데이터 볼륨 추정 & 용량 계획 |
| 문서 ID | DBA-05 |
| 버전 | v0.1 Draft |
| 작성일 | 2026-05-11 |
| 작성자 | DBA Agent |
| 검토자 | DevLead, PM, BackendSenior |
| 상태 | 초안 |
| 대상 DBMS | PostgreSQL 15+ |

---

## 1. 문서 개요

Planner 비기능 요구사항 — **테넌트 1,000개·회원 1천만·서지 5천만건** — 을 기준으로 도서관 유형별 데이터 볼륨을 추정하고, 5년 누적 예측, 스토리지·HA·백업·아카이브 정책을 수립한다.

---

## 2. 도서관 유형별 1관 기준 볼륨 (단일 관 기준 연간)

### 2.1 핵심 지표 매트릭스

| 지표 | 학교 | 대학·전문 | 공공(중소) | 공공(대형) | 다관통합(시) |
|---|---|---|---|---|---|
| 회원수 | 500~2,000 | 10,000~50,000 | 5,000~30,000 | 50,000~200,000 | 200,000~1,000,000 |
| 신규 서지/년 | 500~3,000 | 5,000~30,000 | 5,000~20,000 | 20,000~100,000 | 50,000~300,000 |
| 누적 서지 | 5,000~30,000 | 100,000~1,000,000 | 30,000~200,000 | 500,000~3,000,000 | 1,000,000~5,000,000 |
| 누적 소장(권) | 5,000~50,000 | 200,000~2,500,000 | 50,000~300,000 | 700,000~5,000,000 | 2,000,000~10,000,000 |
| 대출/년 | 5,000~30,000 | 100,000~500,000 | 50,000~500,000 | 500,000~3,000,000 | 1,000,000~10,000,000 |
| 예약/년 | 200~2,000 | 5,000~20,000 | 5,000~50,000 | 50,000~300,000 | 100,000~1,000,000 |
| 출입이벤트/년 | 50,000~200,000 | 500,000~3,000,000 | 200,000~1,000,000 | 1,000,000~5,000,000 | 5,000,000~30,000,000 |
| 좌석예약/년 | (거의 없음) | 100,000~1,000,000 | 50,000~300,000 | 200,000~1,000,000 | 500,000~3,000,000 |
| 회의실 예약/년 | (드뭄) | 10,000~50,000 | 5,000~30,000 | 20,000~100,000 | 50,000~200,000 |
| 감사로그/년 | 100,000~500,000 | 5,000,000~30,000,000 | 1,000,000~10,000,000 | 10,000,000~50,000,000 | 30,000,000~100,000,000 |
| SIP2 트랜잭션/년 | (해당없음) | 100,000~500,000 | 200,000~1,000,000 | 1,000,000~5,000,000 | 5,000,000~30,000,000 |

### 2.2 트랜잭션 빈도 (피크)

| 도메인 | 피크 TPS | 비고 |
|---|---|---|
| OPAC 검색 | 50~500 | 시험기간 대학 + 대형 공공 |
| 대출/반납 | 10~100 | 카운터 + 자가대출기 합산 |
| 좌석예약 | 50~500 | 시험기간 대학 일시집중 |
| 출입게이트 | 100 (전체) | "동시 출입 100건/초" 요구사항 |
| EAS 이벤트 | 5~20 | |
| 통계 쿼리 | 1~10 | 무거운 쿼리, read replica로 분리 |

---

## 3. 플랫폼(테넌트 1,000개) 통합 추정

### 3.1 가정

- 테넌트 분포: 학교 600 / 공공 250(중소 200 / 대형 50) / 대학 100 / 다관통합 50
- 평균 도서관(`library`) 수: 학교 1.0 / 공공 1.5 / 대학 2.0 / 다관 8.0 = 약 **2,300개 관**
- 5년 운영 후

### 3.2 5년 누적 행수 추정 (전체 테넌트 합)

| 테이블 | 행수 추정 | 1행 평균 크기(bytes) | 데이터 크기 |
|---|---|---|---|
| `tlp_cmn_tenant` | 1,000 | 1,500 | 1.5 MB |
| `tlp_cmn_library` | 2,300 | 1,500 | 3.5 MB |
| `tlp_cmn_member` | 10,000,000 | 2,000 | **20 GB** |
| `tlp_cmn_member_status_history` | 30,000,000 | 300 | 9 GB |
| `tlp_cmn_audit_log` | 5,000,000,000 (5G) | 600 | **3 TB** |
| `tlp_cat_bibliography` | 50,000,000 | 3,000 | **150 GB** |
| `tlp_cat_marc_field` | 750,000,000 (15필드/서지) | 800 | **600 GB** |
| `tlp_cat_marc_record_raw` | 50,000,000 | 4,000 | 200 GB |
| `tlp_cat_authority` | 5,000,000 | 1,500 | 7.5 GB |
| `tlp_col_holding` | 60,000,000 | 500 | 30 GB |
| `tlp_col_copy` | 200,000,000 | 800 | **160 GB** |
| `tlp_col_item_status_history` | 500,000,000 | 200 | 100 GB |
| `tlp_acq_purchase_order_item` | 100,000,000 | 1,000 | 100 GB |
| `tlp_cir_loan` | 5,000,000,000 (5G) | 400 | **2 TB** |
| `tlp_cir_hold` | 500,000,000 | 300 | 150 GB |
| `tlp_cir_fine` | 500,000,000 | 250 | 125 GB |
| `tlp_cir_sip2_transaction` | 5,000,000,000 | 1,500 | **7.5 TB** (1년만 보존 → 1.5 TB) |
| `tlp_acs_access_event` | 30,000,000,000 (30G) | 300 | **9 TB** (5년 보존, 3년 후 콜드) |
| `tlp_acs_eas_alarm` | 50,000,000 | 400 | 20 GB |
| `tlp_fac_seat_reservation` | 5,000,000,000 | 400 | 2 TB |
| `tlp_fac_room_reservation` | 500,000,000 | 600 | 300 GB |
| `tlp_cir_opac_search_log` | 10,000,000,000 | 300 | **3 TB** (6개월 보존 → 300 GB) |
| `tlp_cmn_notification_log` | 5,000,000,000 | 400 | 2 TB |

**합계 (인덱스 제외)**: 약 **20~25 TB** (콜드 파티션 제외, 핫 5 TB / 웜 5 TB / 콜드 10~15 TB)
**인덱스 포함 추정**: 약 **30~40 TB** (인덱스/오버헤드 30~50%)

### 3.3 단일 테넌트 (대형 공공·시통합) 추정

| 항목 | 5년 누적 |
|---|---|
| 회원 | 100만 |
| 서지 | 500만 |
| 소장(권) | 1,000만 |
| 대출 트랜잭션 | 5,000만~1억 |
| 출입 이벤트 | 1억~3억 |
| **데이터 크기** | **약 100~200 GB** |

대형 단일 테넌트 1개가 전체의 5~10% 차지. Database-per-Tenant 분리 후보.

---

## 4. 스토리지 증가율·계획

### 4.1 연간 증가율 가정

| 도메인 | 연간 증가율 (안정기) |
|---|---|
| Catalog (서지·MARC) | 10~15% (신간 입수) |
| Collection (copy) | 5~10% (제적 균형) |
| Member | 5~10% |
| Loan/Hold/Fine | 누적 — 핫 1~2년, 웜 3~5년 |
| Access Event | 핫 6개월, 웜 1년, 콜드 3년 후 |
| Audit Log | 5년 보존, 3년 이상 콜드 |

### 4.2 스토리지 등급(Tier) 분리

| 등급 | 매체 | 용도 | 보존 | 비용/GB |
|---|---|---|---|---|
| Hot | NVMe SSD | 직전 6개월 트랜잭션·전체 마스터 | 6개월 | 高 |
| Warm | SSD | 6개월~3년 트랜잭션·과거 통계 | 3년 | 中 |
| Cold | HDD / 오브젝트 스토리지 | 3년 이상 / 출입로그·감사로그 | 5~10년 | 低 |
| Archive | Glacier / Tape | 법정 보존 만료 전 | 10년+ | 매우 低 |

### 4.3 Hot/Cold 분리 적용 매트릭스

| 테이블 | Hot 기준 | Warm 기준 | Cold 기준 |
|---|---|---|---|
| tlp_cir_loan | 진행중 + 1년 이내 완료 | 1~3년 완료 | 3년+ (파티션 DROP→ 콜드 export) |
| tlp_acs_access_event | 6개월 | 6개월~1년 | 1~5년 |
| tlp_cmn_audit_log | 6개월 | 1년 | 1~5년 |
| tlp_cir_opac_search_log | 1개월 | 1~6개월 | 6개월+ (삭제) |
| tlp_cir_sip2_transaction | 3개월 | 3~12개월 | 1년+ (삭제) |

콜드 이전 절차:
1. 월별 파티션 `DETACH PARTITION`
2. `pg_dump` 또는 COPY로 S3 Parquet export
3. 파티션 DROP (또는 별도 콜드 스키마로 ATTACH)
4. 메타데이터 테이블에 위치 기록

---

## 5. HA(고가용성) 구성

### 5.1 권고 아키텍처

```
                       ┌────────────────────┐
                       │   Application LB   │
                       └─────────┬──────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
       ┌──────▼──────┐                       ┌──────▼──────┐
       │ Primary DB  │ ─── Streaming ──────► │  Standby 1  │  (sync replica, RPO=0)
       │  (Patroni)  │                       │  (failover) │
       └──────┬──────┘                       └─────────────┘
              │
              ├──── Streaming ─────► ┌─────────────┐
              │                      │  Standby 2  │  (async replica, 통계용)
              │                      └─────────────┘
              │
              ├──── WAL Archive ───► [S3 / NFS] (PITR)
              │
              └──── pgBackrest ────► [S3 / Tape] (전체/증분 백업)

       etcd 클러스터 (3노드): Patroni leader election
```

### 5.2 채택 컴포넌트

| 컴포넌트 | 역할 |
|---|---|
| **Patroni** | PostgreSQL HA 자동화 (Leader Election, Failover, Reinit) |
| **etcd 3-node cluster** | Patroni 분산 일관성 저장소 |
| **HAProxy / pgBouncer** | 클라이언트 라우팅, 커넥션 풀 |
| **Streaming Replication** | Primary → Standby 동기/비동기 |
| **WAL Archive (S3)** | PITR 백업 |
| **pgBackrest** | 백업/복구 도구 |
| **Prometheus + pg_exporter + Grafana** | 모니터링 |

### 5.3 RPO / RTO 목표

| 지표 | 목표 | 구현 |
|---|---|---|
| RPO (Recovery Point Objective) | **0~5초** | sync replica + WAL archive |
| RTO (Recovery Time Objective) | **< 60초** | Patroni 자동 failover |
| 백업 RPO | 24시간 | 일 증분 + 주 전체 백업 |
| 백업 RTO | 4시간 | pgBackrest restore + WAL replay |
| 가용성 SLA | **99.9%** (월 43분 다운타임 허용) | Planner 요구사항 가용성 99.5% 초과 |

### 5.4 Failover 절차

1. **자동 Failover (Patroni)**:
   - Primary 장애 감지 (30초 lease 만료) → Standby 1 승격
   - HAProxy 백엔드 health-check로 트래픽 자동 전환
   - 슬레이브 복구 후 자동 reinit
2. **수동 Switchover (계획 점검)**:
   - `patronictl switchover` → 무중단 마스터 교체
3. **DR (Disaster Recovery)**:
   - 별도 region cold standby (월 1회 PITR 복구 훈련)

---

## 6. 백업 정책

### 6.1 백업 종류·주기

| 종류 | 도구 | 주기 | 보존 | 위치 |
|---|---|---|---|---|
| 전체 백업 (Full) | pgBackrest | 주 1회 (일요일 02:00) | 6개월 | S3 + Tape |
| 증분 백업 (Differential) | pgBackrest | 일 1회 (02:00) | 1개월 | S3 |
| WAL Archive (지속) | pgBackrest | 5분 lag | 14일 hot, 6개월 warm | S3 |
| 논리 백업 (pg_dump) | cron | 일 1회 (테넌트별 옵션) | 7일 | NFS |
| 스냅샷 (EBS/볼륨) | 인프라 | 일 1회 | 7일 | 인프라 |

### 6.2 복구 시나리오

| 시나리오 | 복구 방법 | 예상 시간 |
|---|---|---|
| 단일 행 실수 삭제 | History 테이블 또는 audit_log에서 복구 | < 10분 |
| 테이블 전체 손상 | pg_restore (스키마 단위) | < 30분 |
| 특정 시점 복구 (PITR) | pgBackrest restore --target-time | 1~4시간 |
| Primary 장애 | Patroni 자동 failover | < 60초 |
| Region 장애 | DR cold standby 활성화 | 4~8시간 |
| 데이터 센터 전체 손실 | 백업+WAL S3 cross-region | 8~24시간 |

### 6.3 백업 검증

- **월 1회 복구 훈련**: 백업본 임의 시점 복구 후 데이터 정합성 검증.
- **체크섬 자동화**: `pg_checksums` + pgBackrest 무결성 검증.
- **백업 보고서**: PM에게 월간 보고.

---

## 7. WAL · 트랜잭션 부하 관리

### 7.1 WAL 추정

- 대형 테넌트 1일 트랜잭션: ~50 GB WAL
- 평균 압축률 50%로 25 GB/일 × 14일 = **350 GB hot WAL**
- 전체 플랫폼: 약 500 GB ~ 1 TB hot WAL 보존 영역

### 7.2 WAL 튜닝

```ini
# postgresql.conf 권고
wal_level = replica
max_wal_size = 16GB
min_wal_size = 4GB
wal_compression = on
archive_mode = on
archive_command = 'pgbackrest --stanza=tulip archive-push %p'
checkpoint_timeout = 15min
checkpoint_completion_target = 0.9
synchronous_commit = on
synchronous_standby_names = 'ANY 1 (standby1, standby2)'
```

### 7.3 Vacuum / Autovacuum 정책

- 핫 테이블(`tlp_cir_loan`, `tlp_acs_access_event`): scale_factor 0.01~0.05 적용 (위 04 문서 참고).
- 대용량 파티션: 파티션별 autovacuum 별도 튜닝.
- 주 1회 `VACUUM ANALYZE` 전체 수동 점검 (오프피크).

---

## 8. 인프라 사양 가이드

### 8.1 Primary 인스턴스 (대형 운영)

| 항목 | 사양 |
|---|---|
| CPU | 16~32 vCPU |
| RAM | 64~128 GB (shared_buffers 25%, work_mem·maintenance_work_mem 충분) |
| Storage | NVMe SSD 4~8 TB (Hot) + 별도 WAL 디스크 1 TB |
| Network | 10 Gbps |
| IOPS | 30,000+ 보장 |

### 8.2 Standby

- Primary와 동일 사양 (sync replica).
- 통계용 async replica는 약간 낮은 사양 가능 (단, 통계 쿼리는 무거움).

### 8.3 PostgreSQL 주요 파라미터

```ini
shared_buffers = 16GB              # RAM의 25%
effective_cache_size = 48GB        # RAM의 75%
work_mem = 32MB                    # 동시접속 고려, 일부 통계는 SET LOCAL
maintenance_work_mem = 2GB
random_page_cost = 1.1             # SSD
effective_io_concurrency = 200     # NVMe
max_connections = 500              # pgBouncer 앞단 사용 시 충분
max_parallel_workers = 16
max_parallel_workers_per_gather = 4
```

### 8.4 PgBouncer (커넥션 풀)

- Transaction pooling mode 권고.
- max_client_conn 5000, default_pool_size 50.
- BackendSenior와 정합 — Spring Boot HikariCP 풀 크기 정렬.

---

## 9. 도서관 유형별 인프라 권고 (가이드)

| 유형 | DB 사양 | HA |
|---|---|---|
| 학교 (1관, 회원 2천) | 4 vCPU / 16 GB / 200 GB SSD | Primary + 1 Async |
| 공공 중소 (1관, 회원 3만) | 8 vCPU / 32 GB / 500 GB SSD | Primary + 1 Sync |
| 대학 (2~5관, 회원 5만) | 16 vCPU / 64 GB / 2 TB SSD | Primary + 1 Sync + 1 Async |
| 다관 시통합 (5~30관) | 별도 인스턴스 32 vCPU / 128 GB / 8 TB NVMe | Patroni 3노드 + DR |
| **SaaS 플랫폼** | **공유 클러스터** 위 권고 사양, 테넌트 분리는 RLS | Patroni 다중 클러스터 |

---

## 10. 모니터링 핵심 지표 (Capacity)

| 지표 | 임계치 | 조치 |
|---|---|---|
| 스토리지 사용률 | 75% / 85% | 알람 / 확장 검토 |
| WAL 디스크 사용률 | 70% | 아카이브 점검 |
| 커넥션 수 | max_connections 70% | pool 점검 |
| Long-running query | > 5분 | 자동 kill 또는 알람 |
| 복제 lag | > 10초 | 알람 |
| 백업 실패 | 1회 | 즉시 알람 |
| 캐시 히트율 | < 95% | shared_buffers 검토 |
| Dead tuple 비율 | > 20% | VACUUM 즉시 |
| 파티션 자동생성 실패 | 1회 | 즉시 알람 |

---

## 11. 변경 이력

| 버전 | 일자 | 작성자 | 내용 |
|---|---|---|---|
| v0.1 | 2026-05-11 | DBA Agent | 도서관 유형별 볼륨, 5년 누적 추정, Patroni+etcd HA, RPO 5초/RTO 60초, Hot/Warm/Cold 분리 |
