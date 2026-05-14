# 63. 다증권사(Multi-Broker) 통합 테스트 계획

본 문서는 D4 — 다증권사 어댑터(KIS / 키움) 도입에 대한 QA 통합 테스트 계획을
정의한다. 기존 CREON 통합 테스트 절차를 차용하여 3종 어댑터를 동일 기준으로 검증한다.

| 키 | 값 |
|---|---|
| 적용 범위 | CREON / KIS / 키움 어댑터 |
| 모드 | SIM(모의), REAL(실거래) |
| 환경 | dev / staging / prod (prod 는 read-only 점검만) |
| 의존 서비스 | Redis Pub/Sub, PostgreSQL, creon-gateway, kiwoom-gateway |

---

## 1. 검증 목표

1. **포트 일관성**: ``OrderRouterPort`` / ``MarketDataPort`` 시그니처 변경 없음.
2. **기능 동등성**: 3종 어댑터가 동일 입력에 대해 의미적으로 동일한 동작.
3. **격리성**: 한 broker 장애가 타 broker 거래를 차단하지 않음.
4. **Fallback 동작**: 게이트웨이 장애 시 backup broker 로 1회 재시도.
5. **자격증명 보안**: 평문 비밀이 DB/로그에 절대 노출되지 않음.
6. **모드 격리**: SIM ↔ REAL 환경 분리 및 안전 가드 (CREON_TRADE_ENV / KIS_TRADE_ENV / KIWOOM_TRADE_ENV).

---

## 2. 어댑터 회귀 테스트 카탈로그

### 2.1 공통 시나리오 (broker × {CREON, KIS, KIWOOM})

각 broker 별로 동일 케이스를 수행. broker 라벨 차이만 결과에 반영되어야 한다.

| TC ID | 시나리오 | 기대 | CREON | KIS | KIWOOM |
|---|---|---|---|---|---|
| MB-001 | LIMIT 매수 정상 발주 | ACCEPTED + broker_order_no 존재 | ✓ | ✓ | ✓ |
| MB-002 | MARKET 매수 정상 발주 | ACCEPTED | ✓ | ✓ | ✓ |
| MB-003 | LIMIT 매도 — 보유 없음 | E0024 매도수량부족 | ✓ | ✓ | ✓ |
| MB-004 | 호가단위 위반 | E0026 | ✓ | ✓ | ✓ |
| MB-005 | 상하한가 도달 | E0027 | ✓ | ✓ | ✓ |
| MB-006 | 거래정지 종목 | E0028 | ✓ | ✓ | ✓ |
| MB-007 | 미체결 취소 정상 | CANCELED | ✓ | ✓ | ✓ |
| MB-008 | 게이트웨이/외부 미연결 | E0012 | ✓ | ✓ | ✓ |
| MB-009 | 응답 타임아웃 | E0072 | ✓ | ✓ | ✓ |
| MB-010 | 멱등성 키 중복 | 동일 응답 반환 (재발주 없음) | ✓ | ✓ | ✓ |
| MB-011 | Rate Limit 초과 호출 | 자동 대기 → 정상 응답 | ✓ | ✓ | ✓ |
| MB-012 | 시세 조회 (현재가) | QuoteSnapshot 정상 | ✓ | ✓ | ✓ |
| MB-013 | 잔고 조회 | cash/equity 비음수 | ✓ | ✓ | ✓ |
| MB-014 | 헬스비트 발행 (broker 라벨) | broker 필드 정확 | ✓ | ✓ | ✓ |

### 2.2 broker 별 특수 케이스

| TC ID | broker | 시나리오 | 기대 |
|---|---|---|---|
| MB-K01 | KIS | 토큰 만료(EGW00121) → 1회 자동 재시도 | 첫 시도 401-like → 두 번째 시도 200 |
| MB-K02 | KIS | 동시 다중 호출 → 토큰 발급 1회 | Redis 분산락 동작 |
| MB-K03 | KIS | SIM/REAL 도메인 분리 | URL 정확 (29443 vs 9443) |
| MB-K04 | KIS | TR ID 매핑 BUY/SELL × SIM/REAL | VTTC0802U / VTTC0801U / TTTC0802U / TTTC0801U |
| MB-W01 | KIWOOM | OCX 미연결 → mock fallback 알림 | 헬스비트에 connected=false |
| MB-W02 | KIWOOM | SendOrder return≠0 | K0013 → E0023 매핑 |
| MB-W03 | KIWOOM | 화면번호 100개 제한 초과 구독 | K0010 → E0008 |
| MB-C01 | CREON | 1초 12건 안전마진 — 13건 호출 | 마지막 호출은 자동 대기 |

### 2.3 Fallback 시나리오

| TC ID | 시나리오 | 기대 |
|---|---|---|
| MB-F01 | 주=CREON 장애(E0012), 백업=KIS, fallback=ON | 주 1회 실패 → KIS 1회 성공 → ACCEPTED |
| MB-F02 | 주=KIS 장애, 백업=CREON, fallback=ON | KIS 실패 → CREON 성공 |
| MB-F03 | 주=KIS 비즈니스 거부(E0024), fallback=ON | fallback 미적용 — E0024 그대로 전달 |
| MB-F04 | 주=KIS 게이트웨이 timeout(E0072), fallback=OFF | E0072 그대로 raise |
| MB-F05 | 주=백업 동일, fallback=ON | FallbackRouter 미적용 (단일 라우터) |
| MB-F06 | submit fallback 후 cancel | cancel 은 주 broker(KIS) 에만 요청 — backup 호출 없음 |

### 2.4 사용자 설정 흐름

| TC ID | 시나리오 | 기대 |
|---|---|---|
| MB-S01 | GET /settings/brokers — 인증 사용자 | 3종 목록 + preferred + connected[] |
| MB-S02 | POST /settings/brokers/KIS/connect (appkey + appsecret) | DB 에 appkey_enc 저장 (평문 아님) |
| MB-S03 | DB select 검증 | broker_credentials.KIS.appkey_enc 가 base64 (AES-GCM 형식) |
| MB-S04 | PUT /settings/brokers/preference {KIS} | users.preferred_broker=KIS |
| MB-S05 | 주문 발주 → 라우터 선택 | KisLiveOrderRouter 사용 (factory log) |
| MB-S06 | POST /settings/brokers/KIS/disconnect | broker_credentials.KIS 키 제거 |
| MB-S07 | 잘못된 broker (UNKNOWN) 요청 | 400 E0003 |
| MB-S08 | 로그 마스킹 검증 | appkey/appsecret 가 로그에 절대 없음 |

---

## 3. 통합 테스트 Stage (CREON 검증 절차 차용)

기존 ``qa/61_creon_integration_plan.md`` 의 Stage 구조를 그대로 따른다.
각 broker 마다 동일 Stage 를 별도 환경에서 수행.

### Stage 0: 사전 점검 (broker 무관)
- DB 마이그레이션 ``2026_05_add_broker_settings.sql`` 적용
- ``tp_user.broker_status`` 테이블 3행 (CREON/KIS/KIWOOM) 시드 존재
- ORM ``User.preferred_broker`` 컬럼 존재

### Stage 1: Mock 모드 단위 테스트
- KIS: `backend/tests/unit/test_kis_adapter.py` 전수 통과
- 키움: `kiwoom-gateway/tests/test_kiwoom_adapter.py` 전수 통과
- factory: `backend/tests/unit/test_broker_factory.py` 전수 통과

### Stage 2: 게이트웨이 헬스 (broker × dev)
- CREON `9100/healthz` 200
- 키움 `9101/healthz` 200
- KIS 토큰 발급 dry-run (모의투자 도메인)

### Stage 3: SIM 모드 E2E (각 broker)
- 1주 SIM 운영 — 일평균 20건 주문
- 실패율 < 0.5%, fallback 발동 0회 기대

### Stage 4: 카오스 (장애 주입)
- creon-gateway 중지 → 본체 측 ``E0012`` 응답
- KIS 토큰 강제 만료 → 자동 재시도 성공
- 키움 OCX 강제 disconnect → 헬스비트에 connected=false

### Stage 5: Fallback 검증
- ``BROKER_FALLBACK_ENABLED=true`` + ``BROKER_FALLBACK_BACKUP=KIS``
- 주 broker(CREON) 게이트웨이 OFF → 주문 발주 시 KIS 라우터 자동 호출
- 비즈니스 거부 케이스(E0024) 에서 fallback 미발동 검증

### Stage 6: 보안
- gitleaks: APPKEY / appsecret / 비밀번호 평문 없음
- DB dump 검사: ``broker_credentials.*_enc`` 만 존재, 평문 ``appkey`` 키 없음
- 로그 마스킹: KIS appkey/appsecret 로그 미노출

### Stage 7: 모드 격리
- KIS REAL 도메인 차단 (운영 미승인 시) → SIM URL 만 호출 가능 확인
- 사용자 trade_mode=LIVE 진입 가드 (`docs/15_trading_policy.md` §3.2 동일)

### Stage 8: 운영 인수
- 운영자 매뉴얼 (`docs/50_multi_broker_guide.md`) 검수
- 작업스케줄러 register-task.ps1 (CREON + 키움) 정상 등록
- PM 최종 승인 → prod 배포

---

## 4. 자동화 회귀 매트릭스 (CI)

```yaml
# .github/workflows/multi-broker-tests.yml (개념)
jobs:
  test-kis:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q backend/tests/unit/test_kis_adapter.py
  test-broker-factory:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q backend/tests/unit/test_broker_factory.py
  test-kiwoom-gateway:
    runs-on: ubuntu-latest    # mock 모드로 Linux 에서 동작 검증
    steps:
      - run: cd kiwoom-gateway && pytest -q tests/
```

---

## 5. 합격 기준 (Definition of Done)

- [ ] 단위 테스트 100% 통과 (`test_kis_adapter.py` / `test_broker_factory.py` / `test_kiwoom_adapter.py`)
- [ ] 통합 매트릭스 MB-001 ~ MB-014 가 3종 broker × {SIM} 에서 모두 통과
- [ ] Fallback 시나리오 MB-F01 ~ MB-F06 통과
- [ ] 사용자 설정 흐름 MB-S01 ~ MB-S08 통과
- [ ] 기존 CREON 회귀 (`qa/61_creon_integration_plan.md`) 100% 통과
- [ ] gitleaks / 보안 스캔 무결함
- [ ] `docs/50_multi_broker_guide.md` 운영자 검수 완료
- [ ] PM 배포 승인

---

## 6. 리스크 / 미해결 이슈

| ID | 리스크 | 완화책 |
|---|---|---|
| R-MB-01 | KIS WebSocket 시세 — v1 stub 만 제공 | Sprint+1 — `event_subscriber.py` 구현 |
| R-MB-02 | 키움 Real 어댑터 — PyQt 이벤트 루프 통합 복잡 | v1 은 mock + 동기 stub. Real 운영은 별도 워커 프로세스로 분리 |
| R-MB-03 | KIS 호가창 v1 한정 — D1 호가창 작업과 후속 통합 필요 | D1 작업 완료 후 KIS 호가 활성화 |
| R-MB-04 | 사용자별 토큰 분리 시 Redis 키 수 증가 | appkey 해시 16자만 사용, TTL 23h 로 자연 만료 |
| R-MB-05 | 실거래 REAL 자격증명을 사용자 DB 저장하는 정책 | 운영팀 별도 점검: AES_KEY 회전 1년 정책 + 평문 비밀 로그 금지 감사 |
