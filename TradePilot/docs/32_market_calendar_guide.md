# 32. 시장 캘린더(휴장일) 운영 가이드

> **문서 위치**: `docs/32_market_calendar_guide.md`
> **대상**: PM / DevLead / Backend / 운영자 / QA
> **연관 코드**:
> - `database/init/16_calendar_seed.sql` (init 시드)
> - `database/migrations/2026_05_add_market_calendar.sql` (테이블 생성 마이그레이션)
> - `backend/app/models/market.py` (`MarketCalendar`)
> - `backend/app/services/calendar_service.py` (단일 진입점)
> - `backend/app/services/market_service.py` (장 운영 상태 위임)
> - `backend/app/workers/tasks/calendar_tasks.py` (Celery 자동 동기화)
> - `backend/app/api/v1/market.py` (조회/관리자 API)

---

## 1. 개요

KRX(한국거래소) 휴장일은 **법정 공휴일(REGULAR)**, **임시 휴장(TEMPORARY)**, **대체 공휴일(SUBSTITUTE)** 세 가지 유형으로 분류된다.
이전에는 `market_service.py` 에 하드코딩된 `KR_HOLIDAYS` 딕셔너리로 관리했으나, 본 가이드 시점부터는 다음과 같이 바뀐다.

- **저장**: PostgreSQL `tp_market.market_calendar` 테이블 (영구 저장).
- **조회**: 모든 모듈은 `CalendarService` 만 사용한다.
- **갱신**: 매년 1월 2일 09:00 KST Celery Beat 가 `calendar.sync_yearly` 자동 실행.
- **임시휴장**: 운영자가 관리자 API 로 즉시 등록.

---

## 2. 데이터 소스 및 갱신 주기

| 항목 | 값 |
|------|-----|
| **자동 동기화 출처** | `pykrx` (KOSPI 1001 지수 거래일 차집합으로 휴장일 추정) |
| **자동 동기화 주기** | 매년 **1월 2일 09:00 KST** (Celery Beat `calendar-sync-yearly`) |
| **자동 동기화 대상 연도** | 당해 + 익년 (총 2년치) |
| **수동 동기화 가능 시점** | 언제나. `/admin/market/calendar/sync/{year}` |
| **임시휴장 등록** | 운영자 즉시. `/admin/market/calendar/holidays` |
| **캐시** | Redis 30분 TTL. 추가/삭제/동기화 시 invalidate. |
| **타임존** | `Asia/Seoul` (한국 표준시) |

`pykrx` 는 휴장일 한글 명칭을 제공하지 않으므로, 자동 동기화로 등록된 항목의 `holiday_name` 은 일괄 `"휴장일"` 이 된다. 운영자가 사후에 정확한 명칭으로 갱신하거나(같은 날짜 재등록) 또는 시드 데이터로 미리 정확한 이름을 적재해두는 방식을 권장한다.

---

## 3. 데이터 모델

```text
tp_market.market_calendar
├── id BIGSERIAL PK
├── holiday_date DATE UNIQUE  -- 단일 일자 UNIQUE
├── holiday_name VARCHAR(100) -- 신정 / 설날 / 추석 등
├── holiday_type VARCHAR(20)  -- REGULAR / TEMPORARY / SUBSTITUTE
├── market VARCHAR(10)        -- KRX (확장 대비: NYSE 등)
├── description TEXT NULL
├── source VARCHAR(20)        -- pykrx / manual / seed
├── created_at TIMESTAMPTZ
└── updated_at TIMESTAMPTZ
```

- **UNIQUE 제약**: `(market, holiday_date)` + `holiday_date` 단일.
- **CHECK 제약**: `holiday_type ∈ {REGULAR, TEMPORARY, SUBSTITUTE}`, `source ∈ {pykrx, manual, seed}`.

---

## 4. 단일 소스 사용 가이드 (개발자)

```python
from app.services.calendar_service import CalendarService

svc = CalendarService(db)
if not await svc.is_business_day(today):
    return  # 영업일 아님: 시그널/주문 진입 차단

# 다음 영업일(예: 결제일 산정)
settle_date = await svc.next_business_day(trade_date)
```

| 메서드 | 용도 |
|--------|------|
| `is_holiday(date, market='KRX')` | 휴장일 여부 (주말 미포함) |
| `is_business_day(date)` | 평일 + 휴장 아님 |
| `next_business_day(date)` | 이후 가장 가까운 영업일 |
| `previous_business_day(date)` | 이전 가장 가까운 영업일 |
| `business_days_between(start, end)` | 양 끝 포함 영업일 수 |
| `get_holidays(year, market='KRX')` | 연도별 휴장일 목록 |
| `add_holiday(date, name, type='TEMPORARY', source='manual')` | 휴장일 등록 (UPSERT) |
| `remove_holiday(date, market)` | 휴장일 삭제 (감사 로그) |
| `sync_from_krx(year)` | pykrx 동기화 (수동/스케줄) |

> **하지 말 것**: 모듈 내부에서 `weekday()` 와 자체 휴일 리스트를 섞어 쓰지 않는다. 새로운 휴장일이 추가되어도 자동 반영되지 않으면 `KillSwitch`/`OrderService` 에서 잘못 동작할 수 있다.

---

## 5. API

### 5.1 퍼블릭 (인증 불필요)

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/market/calendar?year=YYYY` | 레거시 호환 (간단 응답) |
| GET | `/api/v1/market/calendar/{year}?market=KRX` | 상세 응답 (type/source 포함) |
| GET | `/api/v1/market/calendar/business-day/{YYYY-MM-DD}` | 영업일 여부 + 다음/이전 |
| GET | `/api/v1/market/status` | 장 운영 상태 (KST) |

### 5.2 관리자 (ROLE_ADMIN / ROLE_OPERATOR)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/admin/market/calendar/sync/{year}` | 수동 동기화 (Celery enqueue, 워커 미가용 시 인라인) |
| POST | `/api/v1/admin/market/calendar/holidays` | 임시휴장 추가 |
| DELETE | `/api/v1/admin/market/calendar/holidays/{YYYY-MM-DD}?market=KRX` | 휴장일 삭제 (ADMIN 전용) |

#### 임시휴장 추가 요청 예시

```json
POST /api/v1/admin/market/calendar/holidays
{
  "holiday_date": "2026-04-15",
  "holiday_name": "임시휴장 (시스템 점검)",
  "holiday_type": "TEMPORARY",
  "market": "KRX",
  "description": "시스템 점검을 위한 KRX 임시휴장"
}
```

응답: `201 Created` + 등록된 항목.

---

## 6. 운영자 매뉴얼

### 6.1 연초 점검 체크리스트 (1월 2~5일)

1. `/api/v1/market/calendar/{새해}` 호출 → **자동 동기화 결과 확인**
2. 한국거래소 공시 일정과 대조 (https://www.krx.co.kr → '시장운영' → '거래일정')
3. **명칭 보정**: pykrx 가 자동 등록한 `"휴장일"` → 정식 명칭으로 수정
   - DELETE → POST 순서, 또는 POST(UPSERT) 로 동일 날짜 재등록
4. **TEMPORARY/SUBSTITUTE 누락 점검**: 자동 동기화는 REGULAR 만 대상. 임시휴장/대체공휴일은 운영자가 명시 등록한다.

### 6.2 임시휴장 발생 시 (예: 정부 임시 공휴일 발표)

1. 발표 즉시 `/api/v1/admin/market/calendar/holidays` 로 등록
2. `holiday_type`: `TEMPORARY` (대체공휴일이면 `SUBSTITUTE`)
3. 등록 즉시 30분 캐시는 자동 invalidate → 모든 모듈 즉시 반영

### 6.3 자동 동기화 실패 대응

- 알림 채널로 `[캘린더] 연간 휴장일 자동 동기화 실패` 메시지 수신
- 수동 트리거: `/api/v1/admin/market/calendar/sync/{year}`
- 그래도 실패하면 `pykrx` 패키지 설치 상태 / 외부 KRX 응답 상태 점검
- pykrx 미설치 환경(컨테이너 빌드 실패 등)에서는 시드 데이터로 폴백되어 시스템은 동작 가능

---

## 7. 마이그레이션 / 배포

1. 신규 환경: `database/init/16_calendar_seed.sql` 가 자동 적용됨
2. 기존 환경: `database/migrations/2026_05_add_market_calendar.sql` 수동 적용
   ```bash
   psql $DATABASE_URL -f database/migrations/2026_05_add_market_calendar.sql
   ```
3. Celery Beat 재시작 필요:
   ```bash
   celery -A app.workers.celery_app beat
   ```
4. 워커 큐: `default` (calendar.* 라우팅)

---

## 8. 결정 사항 (Decision Log)

- **시드 vs pykrx**: 시드 데이터를 우선(정확한 한글 명칭) + 연 1회 pykrx 보정. `manual` 소스는 보존(WHERE 조건).
- **REGULAR 만 자동 동기화**: pykrx 는 임시휴장/대체공휴일을 구분 못하므로 운영자 수동 영역으로 분리.
- **단일 시장(KRX) 우선**: `market` 컬럼은 확장 대비. 미국장(NYSE/NASDAQ) 추가 시 별도 동기화 어댑터 필요.
- **30분 캐시**: 임시휴장이 발표되더라도 30분 내 반영. 더 짧게 가져갈 필요 시 invalidate API 별도 추가 검토.

---

## 9. 변경 이력

| 일자 | 작성자 | 내용 |
|------|--------|------|
| 2026-05-13 | BackendDev | 신규 작성 (캘린더 자동화 도입) |
