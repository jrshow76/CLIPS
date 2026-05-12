# TradePilot 부하 / 스모크 테스트 가이드

본 디렉토리는 배포 검증용 스모크 테스트와 핵심 API 부하 테스트를 포함한다.

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

---

## 2. k6 부하 테스트 (`k6_orders_burst.js`)

주문 API 100 RPS / 5분 부하 시나리오. **반드시 SIM 모드만 사용**.

### 종속성
- [k6](https://k6.io) ≥ 0.50

### 실행
```bash
# Staging 환경 (사전에 SIM 사용자 토큰 발급)
BASE_URL=https://staging.internal TOKEN=eyJ... \
  k6 run qa/load/k6_orders_burst.js
```

### 시나리오
- 워밍업: 0 → 30 RPS (30s)
- 부하: 30 → 100 RPS (1m)
- 유지: 100 RPS (3m)
- 정리: 100 → 0 RPS (30s)

### 임계값(SLA)
- 응답 P95 < 500ms
- 응답 P99 < 1500ms
- 실패율 < 1%
- 2xx 성공률 > 99%

### 결과 보고
- 콘솔 요약 출력
- `reports/k6_summary.json` 자동 저장 (Beta 게이트 첨부 의무)

### 사용 시점
- Beta 게이트 통과 직전(`54_release_checklist.md` 2.9)
- 신규 매매 정책 변경 후 회귀 검증
- 인덱스/쿼리 튜닝 전후 성능 비교

---

## 3. 주의사항

- **LIVE 모드로 부하 테스트 절대 금지** — 실주문 발생 위험.
- 사용자 토큰은 일회용으로 발급 후 즉시 폐기.
- 테스트 종료 후 `audit_log` 에 비정상 패턴이 없는지 확인.
- Production 부하 테스트는 PM 사전 승인 필수.

---

## 4. 결함 발견 시 절차

1. `qa/55_bug_template.md` 양식으로 Jira 등록.
2. k6 결과 JSON 첨부 + 그라파나 대시보드 캡쳐.
3. DBA 협업으로 슬로우 쿼리/락 분석.
4. 회귀 자동화 케이스(`backend/tests/qa/`) 추가.
