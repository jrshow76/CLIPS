# TradePilot ML 엔진

LSTM 기반 단기 가격 방향성 예측. 운영 가치를 단순화하기 위해 **3-class 분류**(상승/보합/하락) 모델을 채택했다.

## 모델 종류 (3종)

| 종류 | 학습 대상 | 모델 파일 | 키 패턴 | 임베딩 | 운영 주기 |
|---|---|---|---|---|---|
| INDIVIDUAL | 단일 종목 OHLCV | model.pt | `005930_3d` | 없음 | 주 1회 (per-stock) |
| SECTOR | 섹터 내 종목 통합 | model.pt | `sector_SEMI_3d` | 없음 (가중치 공유) | 매주 일요일 02:00 KST |
| GLOBAL | 전 종목 통합 | model.pt | `global_3d` | nn.Embedding(num_stocks, 8) | 매월 1일 02:00 KST |

세 종류 모두 동일한 LSTM 구조를 기반으로 하며, 입력 차원과 임베딩 결합 방식만 다르다.

## 기본 LSTM 구조

```
입력: (batch, lookback=60, n_features=8) [+ stock_ids (batch,) for GLOBAL]

(GLOBAL only) stock_embedding(num_stocks, 8)
        → broadcast (batch, lookback, 8)
        → concat → (batch, lookback, n_features + 8)

Linear(in_dim -> hidden=64)
    ↓
LSTM(64, 64, num_layers=2, dropout=0.2)
    ↓
LayerNorm(64) → Dropout(0.2)
    ↓
Linear(64 -> 3)
    ↓
Softmax → {DOWN, FLAT, UP}
```

- 파라미터 수
  - INDIVIDUAL / SECTOR: 약 50K (모델 파일 < 250KB)
  - GLOBAL: 약 50K + 8 × num_stocks (1000종목 기준 +8K 파라미터, 모델 파일 < 500KB)

## 피처 (기본 8개)

| 피처      | 변환                       | 비고                  |
|-----------|----------------------------|-----------------------|
| close     | log return                 | 일간 수익률           |
| volume    | log(volume+1)              | scaler 가 z-score 처리 |
| ma5       | close/ma5 - 1              | 단기 이동평균비       |
| ma20      | close/ma20 - 1             | 중기 이동평균비       |
| rsi14     | 0~100 그대로               | scaler 가 정규화      |
| macd      | macd/close                 | 스케일 보정           |
| bb_pct_b  | (close-bb_low)/(bb_up-bb_low) | Bollinger %B       |
| obv       | sign(d) * log(|d|+1)       | OBV 차분 log scale    |

## 라벨링 (3-class)

`horizon` 일 후 수익률 기준:

| 라벨 | 조건                     | 의미 |
|------|--------------------------|------|
| 0    | r < -1%                  | 하락 |
| 1    | -1% <= r < +1%           | 보합 |
| 2    | r >= +1%                 | 상승 |

임계값은 `MLConfig.up_threshold` / `down_threshold` 로 조정 가능.

## 학습 절차

### 단일 종목 (INDIVIDUAL)
1. OHLCV 로드 → 피처 변환 → 라벨 생성
2. 시간 분할 (앞 85% train / 뒤 15% val, 셔플 금지)
3. StandardScaler fit (train only) → transform
4. CrossEntropyLoss(class_weight=inverse_freq) + AdamW + ReduceLROnPlateau
5. EarlyStopping(patience=5) + best 체크포인트 저장

### 멀티 종목 (SECTOR / GLOBAL)
1. 각 종목 OHLCV → 피처/라벨/윈도잉 (시간 분할은 종목별로 수행)
2. 종목별 train/val 을 합쳐 통합 배열 생성
3. **샘플 가중치**(GLOBAL only): 데이터 양이 적은 종목 가중치 증가 (mean=1.0 정규화)
4. StandardScaler 는 통합 train 데이터로 fit
5. 모델 학습 시 종목 ID (GLOBAL은 임베딩, SECTOR는 비사용) + 시계열
6. 검증 메트릭: 글로벌 정확도 + 종목별 정확도 + macro F1

학습 산출물 (`{ML_MODEL_DIR}/<model_key>/`):
- `model.pt`      - state_dict
- `scaler.joblib` - 학습 데이터로 fit 된 StandardScaler
- `meta.json`     - `model_kind`/`identifier`/`stock_to_id`/`per_stock_val_acc` 등 풀 메타

## 데이터셋 크기 권장

| 종류 | 학습 데이터 | 비고 |
|---|---|---|
| INDIVIDUAL | 최소 2~3년 일봉 (>500 영업일) | 샘플 부족 시 SECTOR/GLOBAL 폴백 권장 |
| SECTOR | 섹터당 5~15 종목 × 3년 | 종목당 ~700 sample → 합산 3500~10500 |
| GLOBAL | 전 종목 × 3~5년 | 합산 50000~150000 sample |

## 추론

### 단일 모델 추론
```python
from app.services.ml_engine import MLConfig, predict_from_ohlcv

config = MLConfig(stock_code="005930", horizon_days=3)
result = predict_from_ohlcv(ohlcv_df, config)
# result.direction, result.confidence, result.prob_up/flat/down
```

### 자동 선택 (registry 기반)
```python
from app.services.ml_engine import predict_auto

result = predict_auto(ohlcv_df, stock_code="005930", horizon=3, sector_code="SEMI")
# 우선순위: INDIVIDUAL(fresh) → SECTOR → GLOBAL
```

### 앙상블 (가중 평균)
```python
from app.services.ml_engine import predict_ensemble

ens = predict_ensemble(
    ohlcv=ohlcv_df,
    stock_code="005930",
    horizon=3,
    sector_code="SEMI",          # SECTOR 모델 선택용
    models=["INDIVIDUAL", "SECTOR", "GLOBAL"],
    weights=None,                # None → 기본 가중치
)
# ens.direction, ens.confidence, ens.contributions
```

## 앙상블 정책

### 기본 가중치
| 시나리오 | INDIVIDUAL | SECTOR | GLOBAL |
|---|---|---|---|
| 3종 모두 사용 가능 | 0.5 | 0.3 | 0.2 |
| 개별 모델 없음     | -   | 0.6 | 0.4 |
| 섹터 모델 없음     | 0.7 | -   | 0.3 |
| 글로벌만 사용 가능 | -   | -   | 1.0 |

- 누락 모델은 가중치 0 → 활성 모델들로 자동 재정규화
- `weights` 인자로 사용자 정의 가중치 지정 가능

### 결과 형식
```python
{
    "direction": "UP",
    "confidence": 0.71,
    "prob_up": 0.71, "prob_flat": 0.20, "prob_down": 0.09,
    "used_kinds": ["INDIVIDUAL", "SECTOR", "GLOBAL"],
    "contributions": {
        "INDIVIDUAL": {"model_key": "005930_3d", "prob_up": 0.80, ..., "weight": 0.5},
        "SECTOR":     {"model_key": "sector_SEMI_3d", ..., "weight": 0.3},
        "GLOBAL":     {"model_key": "global_3d", ..., "weight": 0.2},
    }
}
```

## 운영 정책

- **추론 큐**: Celery `ml` 큐. 5분 단위 종목별 트리거 + 캐시 30분.
- **학습 큐**: 동일 `ml` 큐. Redis 락(`ml:train:lock`, TTL 2시간) 으로 동시성 1로 제한.
- **스케줄러**:
  - 매일 KST 09:05: 활성 종목 × horizon=1 일괄 추론 (앙상블)
  - 매일 KST 14:30: 활성 종목 × horizon=[1,3,5] 일괄 추론 (앙상블)
  - 매주 일요일 KST 02:00: `ml.train_all_sectors` (모든 섹터 직렬 학습)
  - 매월 1일 KST 02:00: `ml.train_global` (전 종목 글로벌 모델)
- **재학습 트리거**:
  - 종목별: 7일 경과 또는 정확도 5%p 이상 하락
  - 섹터: 주 1회 + 신규 종목 5개 이상 편입
  - 글로벌: 월 1회 + 임베딩 vocab 변경 시

## 모델 선택 우선순위 (registry.get_model_for_stock)

1. 종목별 모델이 있고 `is_fresh()` (7일 이내 학습) → **INDIVIDUAL**
2. 섹터 모델이 있으면 → **SECTOR**
3. 글로벌 모델이 있으면 → **GLOBAL**
4. 종목별 모델이 stale 이라도 있으면 fallback 으로 반환
5. 없으면 `None`

## 한계 및 주의사항

1. **과적합 위험 (INDIVIDUAL)**: 60일 lookback × 3년 데이터는 ~700 sample.
   샘플 부족 위험이 크므로 본 작업의 SECTOR/GLOBAL 모델로 보완하는 것이 핵심.
2. **분포 변화 (distribution shift)**: 시장 체제 전환 시 글로벌 모델도 예측력 하락.
   주간/월간 재학습으로 보완하나 급격한 변화는 한계.
3. **신규 상장 종목 (cold start)**: GLOBAL 모델의 종목 임베딩 vocab 에 없는 종목은
   인덱스 0 (warm start) 으로 폴백. 정확도 보장 어려움 → SECTOR 모델 우선 사용 권장.
4. **매크로 이벤트 미반영**: 가격/거래량/지표만 사용. FOMC, 어닝, 정책 이벤트 직전/후
   추론 신뢰도는 낮다.
5. **클래스 불균형**: 보합(FLAT) 비중 우세. class_weight 자동 보정 적용했으나
   threshold(±1%) 를 종목/섹터 변동성에 맞춰 조정 권장.
6. **백테스트 룩어헤드**: 추론 시점 ≤ 진입 시점 - 1일 보장 필요. `ml_signal` 전략은
   `shift(1)` 처리되어 있음.

## 사용 예 (개발/CI)

torch / DB 미설치 환경에서도 합성 데이터로 검증:

```bash
export ML_USE_SYNTHETIC=true
pytest tests/unit/test_ml_engine.py tests/unit/test_ml_multistock.py
```

- `test_ml_engine.py`: 단일 모델 dataset/forward/학습/추론 검증
- `test_ml_multistock.py`: 섹터/글로벌 모델 forward/학습/우선순위/앙상블 검증

## 참고 문서

- `docs/49_ml_multistock_guide.md`: 멀티 모델 운영 가이드, 재학습 결정 트리, 평가 지표
- `docs/13_api_requirements.md` §12: ML API 명세
