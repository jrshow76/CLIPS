# TradePilot 부하 / 스모크 테스트 가이드

본 디렉토리는 배포 검증용 스모크 테스트와 핵심 API/WS/백테스트 부하 테스트, SLA 정의, 튜닝 가이드를 포함한다.

## 디렉토리 구성

```
qa/load/
├── README.md                       # 본 문서
├── smoke.sh                        # HTTP 스모크 (배포 직후 헬스 체크)
├── smoke_https.sh                  # HTTPS 스모크 (보안 헤더 포함)
├── k6_orders_burst.js              # 주문 API 100 RPS / 5분
├── k6_signals_burst.js             # 시그널 조회 200 RPS / 5분 (신규)
├── k6_ws_burst.js                  # WebSocket 1,000 동시 연결 / 5분
├── k6_api_mixed.js                 # 혼합 워크로드 50 VU / 10분 (신규)
├── k6_backtest_concurrent.js       # 백테스트 동시 10건 (신규)
├── run_all_loads.sh                # 시나리오 일괄 실행 + 결과 수집 (신규)
├── analyze_results.py              # 결과 JSON → Markdown 분석 (신규)
├── 80_load_test_report.md          # 부하 테스트 결과 보고서 (신규)
├── 81_tuning_recommendations.md    # 튜닝 권장사항 P0/P1/P2 (신규)
├── 82_sla_definition.md            # API/WS/매매/백테스트/ML SLA (신규)
└── reports/                        # 실행 결과 (gitignore 권장)
```

---

## 1. 스모크 테스트 (`smoke.sh`)

배포 직후 핵심 GET 엔드포인트 30개의 응답을 검증한다.

### 종속성
- `bash`, `curl`, `jq`

### 실행
```bash
# 토큰 없이 (공개 엔드포인트만 200)
BASE_URL=http://localhost:8000 bash qa/load/smoke.sh

# 인증 필요 엔드포인트 포함
BASE_URL=http://localhost:8000 TOKEN=eyJ... bash qa/load/smoke.sh
```

### 종료 코드
- `0`: 모든 엔드포인트 통과 (허용 코드 범위 내)
- `1`: 1개 이상 실패

### 사용 시점
- 배포 D-day 직후 헬스 체크
- CI 파이프라인 deploy 단계 후
- 운영 중 의심 사례 발생 시 1차 진단

### HTTPS 환경
`smoke_https.sh` 는 동일 흐름에 추가로 HSTS, X-Frame-Options, Server 헤더 노출, `/metrics` 외부 차단, HTTP→HTTPS 리디렉션을 검증.

---

## 2. k6 부하 테스트

### 2.1 시나리오 일람

| 스크립트 | 시나리오 | RPS / VU | 지속 | SLA (P95) |
|---|---|---:|---:|---:|
| `k6_orders_burst.js` | 주문 (SIM) | 100 RPS | 5분 | < 500ms |
| `k6_signals_burst.js` | 시그널 조회 | 200 RPS | 5분 | < 300ms |
| `k6_ws_burst.js` | WebSocket | 1,000 conn | 5분 | < 1500ms (핸드셰이크) |
| `k6_api_mixed.js` | 혼합 (로그인→대시보드→차트→시그널→주문) | 50 VU | 10분 | < 800ms |
| `k6_backtest_concurrent.js` | 백테스트 동시 | 10건 | 가변 | < 1800s (작업 P95) |

### 2.2 종속성
- [k6](https://k6.io) ≥ 0.50

### 2.3 단일 실행
```bash
# 주문 부하
BASE_URL=https://staging.internal TOKEN=eyJ... \
  k6 run qa/load/k6_orders_burst.js

# 시그널 조회
BASE_URL=https://staging.internal TOKEN=eyJ... \
  k6 run qa/load/k6_signals_burst.js

# 혼합 워크로드 (로그인부터 시작)
BASE_URL=https://staging.internal \
  TEST_USERNAME=loadtest@example.com TEST_PASSWORD='...' \
  k6 run qa/load/k6_api_mixed.js

# WebSocket
BASE_URL=wss://staging.internal TOKEN=eyJ... \
  k6 run qa/load/k6_ws_burst.js

# 백테스트 (오래 걸림, 별도 실행 권장)
BASE_URL=https://staging.internal TOKEN=eyJ... N_JOBS=10 \
  k6 run qa/load/k6_backtest_concurrent.js
```

### 2.4 일괄 실행

```bash
# 백테스트 제외, 나머지 4종 순차 실행
BASE_URL=https://staging.internal TOKEN=eyJ... \
  SKIP_BACKTEST=1 \
  bash qa/load/run_all_loads.sh

# 특정 시나리오만
SCENARIOS="orders signals" \
  BASE_URL=https://staging.internal TOKEN=eyJ... \
  bash qa/load/run_all_loads.sh
```

결과는 `qa/load/reports/<TIMESTAMP>_<name>.json` 및 분석 보고서 `<TIMESTAMP>_analysis.md` 로 저장된다.

### 2.5 결과 분석

```bash
python3 qa/load/analyze_results.py \
  --reports-dir qa/load/reports \
  --timestamp 20260514_100000 \
  --out qa/load/reports/20260514_100000_analysis.md

# 베이스라인 회귀 비교
python3 qa/load/analyze_results.py \
  --reports-dir qa/load/reports \
  --timestamp 20260514_100000 \
  --baseline qa/load/reports/baseline.json \
  --out qa/load/reports/20260514_100000_analysis.md
```

---

## 3. SLA 및 보고서

- **SLA 정의**: `82_sla_definition.md` — API/WS/매매/백테스트/ML 별 P95/P99/가용성, 측정 방법, Prometheus 알림 룰.
- **결과 보고서**: `80_load_test_report.md` — 시나리오별 결과 표, 병목 분석, 임계점.
- **튜닝 권장**: `81_tuning_recommendations.md` — P0/P1/P2 우선순위, 검증 방법.

---

## 4. CI 통합 (Nightly Load Test)

### 4.1 GitHub Actions 워크플로우 (예시)

`.github/workflows/load-nightly.yml`:
```yaml
name: nightly-load-test
on:
  schedule:
    - cron: '0 17 * * 0-4'   # 매주 일~목 02:00 KST (UTC 17:00)
  workflow_dispatch:

jobs:
  load:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
            --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
            | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update && sudo apt-get install -y k6
      - name: Run load tests
        env:
          BASE_URL: ${{ secrets.STAGING_BASE_URL }}
          TOKEN:    ${{ secrets.STAGING_LOAD_TOKEN }}
        run: |
          SKIP_BACKTEST=1 bash qa/load/run_all_loads.sh
      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: load-reports-${{ github.run_id }}
          path: qa/load/reports/
      - name: Regression compare
        if: success()
        run: |
          python3 qa/load/analyze_results.py \
            --reports-dir qa/load/reports \
            --timestamp $(ls qa/load/reports/*_meta.json | tail -1 | xargs basename | sed 's/run_//;s/_meta.json//') \
            --baseline qa/load/reports/baseline.json \
            --out qa/load/reports/regression.md
      - name: Notify Slack on regression
        if: failure()
        run: |
          curl -X POST -H 'Content-Type: application/json' \
            --data "{\"text\":\":warning: nightly load test 회귀 (5% 초과) - run ${{ github.run_id }}\"}" \
            ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 4.2 베이스라인 관리
- `qa/load/reports/baseline.json` 은 최근 안정 릴리즈의 결과를 수동으로 commit (PM 승인).
- 새 베이스라인 적용 시 PR 에 사유 (예: P0-1 튜닝 적용 후 P95 30% 단축) 명시.
- 5% 회귀 감지 시 자동으로 Slack 알림 + GitHub Issue 자동 생성 (`gh issue create` 추가 가능).

### 4.3 결과 회귀 비교 정책
| 변동 | 액션 |
|---|---|
| P95 < +5% | OK (정상 변동) |
| +5% ≤ P95 < +10% | Slack 경고 + DevLead 리뷰 |
| P95 ≥ +10% | GitHub Issue 자동 생성, P1 priority |
| 실패율 +0.5%p | 즉시 Slack critical |
| SLA 위반 | 야간 배포 차단 |

---

## 5. 주의사항

- **LIVE 모드로 부하 테스트 절대 금지** — 실주문 발생 위험.
- 사용자 토큰은 일회용으로 발급 후 즉시 폐기.
- 테스트 종료 후 `audit_log` 에 비정상 패턴이 없는지 확인.
- Production 부하 테스트는 PM 사전 승인 필수.
- nginx `zn_order=3r/s` 등 per-IP rate limit 으로 인해 staging 부하 테스트 IP를 별도 whitelist 필요 (자세한 내용은 `81_tuning_recommendations.md` P0-4 참조).

---

## 6. 결함 발견 시 절차

1. `qa/55_bug_template.md` 양식으로 Jira 등록.
2. k6 결과 JSON (`qa/load/reports/`) 첨부 + 그라파나 대시보드 캡쳐.
3. DBA 협업으로 슬로우 쿼리/락 분석.
4. 회귀 자동화 케이스(`backend/tests/qa/`) 추가.
5. 튜닝 적용 후 베이스라인 갱신 PR 발의.

---

## 7. 참고
- `docs/30_operations_runbook.md` — 일일 운영 절차, 비상 대응
- `docs/40_cicd_pipeline.md` — CI/CD 파이프라인
- `docs/41_nginx_tls_guide.md` — nginx/TLS 설정
- `docs/44_logging_policy.md` — 로깅 정책
