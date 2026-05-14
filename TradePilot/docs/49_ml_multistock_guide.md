# ML 멀티 종목 공통 모델 운영 가이드

본 문서는 TradePilot ML 엔진의 **섹터 공통 모델 / 글로벌 공통 모델 / 앙상블 추론** 운영 절차를 정리한다.
기존 종목별 단일 모델(`INDIVIDUAL`)만으로는 샘플 부족과 과적합 위험이 크므로, 같은 LSTM 구조를
공유하는 다층 모델로 확장한다.

관련 코드:
- 모델: `backend/app/services/ml_engine/model.py`
- 데이터셋: `backend/app/services/ml_engine/dataset.py`
- 학습: `backend/app/services/ml_engine/trainer.py`
- 추론/앙상블: `backend/app/services/ml_engine/predictor.py`
- 레지스트리: `backend/app/services/ml_engine/registry.py`
- Celery 태스크: `backend/app/workers/tasks/ml_tasks.py`
- Beat 스케줄: `backend/app/workers/celery_app.py`
- API: `backend/app/api/v1/ml_predictions.py`

---

## 1. 모델 종류 요약

| 종류 | 키 패턴 | 입력 | 임베딩 | 저장 위치 |
|---|---|---|---|---|
| INDIVIDUAL | `{stock_code}_{horizon}d` | OHLCV 1종목 | 없음 | `{ML_MODEL_DIR}/<key>/` |
| SECTOR | `sector_{sector_code}_{horizon}d` | OHLCV 다종목(섹터 내) | 없음 (가중치 공유) | `{ML_MODEL_DIR}/<key>/` |
| GLOBAL | `global_{horizon}d` | OHLCV 다종목(전 종목) | `nn.Embedding(num_stocks, 8)` | `{ML_MODEL_DIR}/<key>/` |

각 저장 폴더에는 `model.pt`, `scaler.joblib`, `meta.json` 3개 파일이 존재한다.

`meta.json` 의 `model_kind` 필드로 종류를 식별한다.

---

## 2. 학습 절차

### 2.1 섹터 모델

```bash
# Celery 태스크 직접 호출 (관리자)
celery call ml.train_sector \
  --kwargs='{"job_id":"sec-SEMI-1d-001","sector_code":"SEMI","stock_codes":["005930","000660",...],"horizon":1}'

# 또는 REST API
curl -X POST /api/v1/ml/train/sector/SEMI \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"horizon": 1}'   # stock_codes 생략 시 DB 자동 조회
```

### 2.2 글로벌 모델

```bash
celery call ml.train_global \
  --kwargs='{"job_id":"global-1d-001","horizon":1}'

curl -X POST /api/v1/ml/train/global \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"horizon": 1}'
```

### 2.3 자동 스케줄 (Celery Beat, KST)

| 작업 | 스케줄 | 비고 |
|---|---|---|
| `ml.train_all_sectors` | 매주 일요일 02:00 | 모든 섹터 직렬 학습 (CPU 보호) |
| `ml.train_global` | 매월 1일 02:00 | 전 종목 글로벌 모델 |
| `ml.batch_predict` (앙상블) | 매일 09:05 / 14:30 | horizons=[1], [1,3,5] |

### 2.4 학습 동시성 락

`Redis SETNX ml:train:lock` (TTL 2시간) 으로 한 번에 한 학습만 수행한다.
한 학습이 진행 중일 때 다른 학습 태스크는 `SKIPPED` 로 종료된다.

---

## 3. 추론 절차

### 3.1 동기 앙상블 (권장)

```bash
curl -X POST /api/v1/ml/predict \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "005930",
    "horizon": 3,
    "ensemble": true,
    "sector_code": "SEMI"
  }'
```

응답:
```json
{
  "data": {
    "stock_code": "005930",
    "horizon": 3,
    "direction": "UP",
    "confidence": 0.71,
    "prob_up": 0.71, "prob_flat": 0.20, "prob_down": 0.09,
    "asof_date": "2026-05-14",
    "used_kinds": ["INDIVIDUAL", "SECTOR", "GLOBAL"],
    "contributions": {
      "INDIVIDUAL": {"model_key": "005930_3d", "prob_up": 0.80, ..., "weight": 0.5},
      "SECTOR":     {"model_key": "sector_SEMI_3d", ..., "weight": 0.3},
      "GLOBAL":     {"model_key": "global_3d", ..., "weight": 0.2}
    }
  }
}
```

### 3.2 단일 자동 선택 (Python)

```python
from app.services.ml_engine import predict_auto
result = predict_auto(ohlcv_df, "005930", horizon=3, sector_code="SEMI")
# registry.get_model_for_stock 우선순위에 따라 단일 모델 사용
```

### 3.3 모델별 비교 (디버그)

```bash
curl /api/v1/ml/comparison/005930?horizon=3&sector_code=SEMI
```

개별/섹터/글로벌/앙상블 결과를 한번에 비교 가능.

---

## 4. 앙상블 가중치 정책

### 기본 가중치

| 시나리오 | INDIVIDUAL | SECTOR | GLOBAL |
|---|---|---|---|
| 3종 모두 사용 | 0.5 | 0.3 | 0.2 |
| INDIVIDUAL 없음 | - | 0.6 | 0.4 |
| 자동 재정규화 | (누락 모델 제외 후 합=1.0 정규화) | | |

### 사용자 정의

```python
result = predict_ensemble(
    ohlcv, "005930", horizon=3, sector_code="SEMI",
    weights={"INDIVIDUAL": 0.7, "SECTOR": 0.2, "GLOBAL": 0.1}
)
```

---

## 5. 모델 선택 우선순위 (registry)

`registry.get_model_for_stock` 의 의사 코드:

```
def get_model_for_stock(stock_code, horizon, sector_code):
    ind = INDIVIDUAL 모델 조회
    if ind 존재 AND ind 7일 이내 학습:
        return ind                          # 최신 개별 모델 우선
    if sector_code 주어짐 AND SECTOR 모델 존재:
        return SECTOR
    if GLOBAL 모델 존재:
        return GLOBAL
    if ind 존재 (stale 일지라도):
        return ind                          # 마지막 fallback
    return None
```

---

## 6. 재학습 결정 트리

```
[추론 요청 진입]
       │
       ▼
INDIVIDUAL fresh?  ── Yes → INDIVIDUAL 사용
       │ No
       ▼
INDIVIDUAL 학습일 > 7일?    ── Yes → 비동기 재학습 큐잉 (ml.train) + 폴백
       │
       ▼
INDIVIDUAL 검증정확도 baseline 대비 5%p 이상 하락?
       │
       ├─ Yes → 강제 재학습 큐잉
       │
       └─ No  → 폴백 사용

[섹터 모델]
주간 일괄 학습 (일요일 02:00)
+ 신규 종목 5개 이상 편입 시 즉시 재학습

[글로벌 모델]
월간 일괄 학습 (1일 02:00)
+ 종목 마스터 vocab 변경 시 즉시 재학습 (임베딩 차원 보존)
```

---

## 7. 평가 지표

학습 결과 `meta.json` 및 학습 상태 응답에 포함되는 지표:

| 지표 | 의미 | 목표 |
|---|---|---|
| `best_val_acc` | 글로벌 검증 정확도 | > 0.40 (베이스라인 0.33) |
| `best_val_f1` | macro F1 (클래스 균형) | > 0.35 |
| `per_stock_val_acc` | 종목별 검증 정확도 (SECTOR/GLOBAL) | > 0.35 (개별 종목 기준) |
| `confusion_matrix` | 3x3 혼동행렬 | 대각선 우세 |
| `model_param_count` | 학습 가능 파라미터 수 | < 100K (개별/섹터), < 200K (글로벌) |
| `duration_sec` | 학습 소요 시간 (초) | < 600 (100종목×5년 CPU) |

### 운영 중 모니터링

매주 백테스트 회귀로 다음을 트래킹:
- `cumulative_return` (모델별)
- `win_rate` (개별/섹터/글로벌/앙상블 비교)
- `accuracy_drift` (최근 30일 검증 정확도)

---

## 8. 신규 종목 (cold start) 처리

GLOBAL 모델은 학습 시점의 종목 vocab 에 종속된다. 신규 상장 종목 처리 정책:

1. **즉시 단계**: SECTOR 모델 또는 INDIVIDUAL 폴백 사용 (글로벌은 인덱스 0 warm start)
2. **단기**: 신규 종목 데이터가 200영업일 이상 누적되면 SECTOR 재학습 (자동)
3. **장기**: 다음 월간 GLOBAL 재학습 시 vocab 확장 (`num_stocks` 증가) → 모델 처음부터 재학습

---

## 9. 분포 변화 (distribution shift) 대응

| 신호 | 액션 |
|---|---|
| 검증 정확도가 baseline 대비 5%p 이상 하락 | 해당 모델 즉시 재학습 |
| 시장 체제 전환 (예: 약세장 → 강세장) | 모든 모델 재학습 우선순위 상향 |
| 매크로 이벤트 직전/직후 | `min_confidence` 임계값 일시 상향 (예: 0.6 → 0.8) |

---

## 10. 한계 및 주의사항

1. **GLOBAL 모델 학습 비용**: 100종목 × 5년 × epochs=10 학습 시 CPU 환경에서 약 10~20분 소요.
   야간 시간대(02:00) 에 스케줄링하여 운영 영향 최소화.
2. **메모리 사용**: 통합 데이터셋이 GB 단위로 커질 수 있으므로 `batch_size` 와 `lookback_days` 를
   환경에 맞게 조정. 권장: batch_size=128~256.
3. **scaler 일관성**: 학습 시 fit 한 scaler 는 추론에 그대로 사용. 종목/섹터별로 분리하지 않으므로
   극단적 이상치 종목(예: 액면분할 직후)은 학습 데이터에서 제외 권장.
4. **임베딩 freeze 정책**: GLOBAL 모델 재학습 시 임베딩을 random init 부터 시작하므로 동일 종목의
   임베딩 벡터가 학습마다 달라진다. **재학습 후에는 모든 INDIVIDUAL/SECTOR 모델보다 우선순위가
   낮은 채로 자연스럽게 적용**되므로 운영상 큰 영향은 없으나, 향후 임베딩 warm start 도입 가능.
5. **백테스트 룩어헤드 검증**: 추론 시점이 진입 시점 - 1일 이상이어야 함. `ml_signal` 전략은
   `shift(1)` 처리되어 있다.

---

## 11. 핵심 결정 (5줄)

1. SECTOR/GLOBAL 모델은 INDIVIDUAL 과 동일한 LSTM 백본을 공유하되, GLOBAL 만 `nn.Embedding(num_stocks, 8)` 추가
2. 학습 동시성은 Redis 락(`ml:train:lock`)으로 1개로 제한 (CPU 보호)
3. 추론 우선순위 INDIVIDUAL(fresh) → SECTOR → GLOBAL, 앙상블 기본 가중치 0.5/0.3/0.2
4. 모든 모델 파일은 `{ML_MODEL_DIR}/<model_key>/` 하위에 `model.pt + scaler.joblib + meta.json` 구조로 통일
5. 백테스트 통합은 `ensemble=true` 옵션으로 `ml_ensemble_predictions` attrs 우선 사용 (룩어헤드 방지 `shift(1)` 유지)
