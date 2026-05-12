# TradePilot ML 엔진

LSTM 기반 단기 가격 방향성 예측. 운영 가치를 단순화하기 위해 **3-class 분류**(상승/보합/하락) 모델을 채택했다.

## 모델 구조

```
입력: (batch, lookback=60, n_features=8)

Linear(n_features -> 64)
    ↓
LSTM(64, 64, num_layers=2, dropout=0.2)
    ↓
LayerNorm(64)
    ↓
Dropout(0.2)
    ↓
Linear(64 -> 3)
    ↓
Softmax → {DOWN, FLAT, UP}
```

- 파라미터 수: 약 50K개 (CPU 친화적)
- 모델 파일: state_dict 기준 < 250KB

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

1. OHLCV 로드 (DB `tp_market.price_daily` 또는 `ML_USE_SYNTHETIC=true` 합성)
2. 지표 부착 (`backtest_engine.indicators.attach_indicators`)
3. 피처 변환 (`features.build_features`)
4. 라벨 생성 (`features.label_horizon_class`)
5. 윈도잉: t-lookback..t-1 → 라벨[t+horizon]
6. **시간 기반 분할**: 앞 85% train, 뒤 15% val (랜덤 셔플 금지)
7. **StandardScaler fit은 train 데이터만**, val/추론은 transform
8. CrossEntropyLoss(class_weight=inverse_freq) + AdamW + ReduceLROnPlateau
9. EarlyStopping(patience=5, val_loss 기준) + best 체크포인트 저장

학습 산출물 (`{ML_MODEL_DIR}/{stock_code}_{horizon}d/`):
- `model.pt`      - state_dict
- `scaler.joblib` - 학습 데이터로 fit 된 StandardScaler
- `meta.json`     - 피처/하이퍼/검증 메트릭/이력

## 추론

```python
from app.services.ml_engine import MLConfig, predict_from_ohlcv

config = MLConfig(stock_code="005930", horizon_days=3)
result = predict_from_ohlcv(ohlcv_df, config)
# result.direction = "UP" | "FLAT" | "DOWN"
# result.confidence = 0.72
# result.prob_up / prob_flat / prob_down
```

- 최근 lookback_days(=60) 행만 사용
- DB 저장 형식 변환: `predictions_to_ml_record(result, last_close)` →
  `ml_predictions` 테이블에 INSERT (model_version = "lstm-v1-{direction}-{conf%}")

## 운영 정책

- **추론 큐**: Celery `ml` 큐. 5분 단위 종목별 트리거 + 캐시 30분.
- **학습 큐**: 동일 `ml` 큐. 학습 시간이 길어 단일 워커 점유 가능. (time_limit=3600s)
- **스케줄러**:
  - 매일 KST 09:05: 활성 종목 × horizon=1 일괄 추론
  - 매일 KST 14:30: 활성 종목 × horizon=[1,3,5] 일괄 추론
- **재학습 주기**: 종목별 주 1회 자동 + 검증 정확도가 baseline 대비 5%p 이상 하락 시 강제 트리거.
- **모델 평가**: 운영 중 매주 백테스트 회귀로 (cumulative_return, win_rate) 트래킹.

## 한계 및 주의사항

1. **과적합 위험**: 60일 lookback × 3년 데이터는 ~700 sample. 학습 시 dropout=0.2 + EarlyStopping 으로 보수적 운영, 검증 정확도가 baseline(33%) 이하면 모델 비활성화 권장.
2. **매크로 이벤트 미반영**: 본 모델은 가격/거래량/지표만 사용. FOMC, 어닝 콜, 정책 발표 등은 직접 피처화하지 않으므로 이벤트 직전/직후 추론 신뢰도는 낮다.
3. **체제 변화(regime shift)**: 시장 체제가 급변할 때(예: 약세장 → 강세장 전환) 과거 데이터로 학습된 모델의 정확도가 급락할 수 있다. **drift 모니터링이 필수**.
4. **클래스 불균형**: 보합(FLAT) 비중이 크게 우세할 가능성. class_weight 자동 보정 적용했으나, threshold(±1%) 를 종목 변동성에 맞춰 조정 권장.
5. **백테스트 룩어헤드 검증**: 시계열 분할만으로 누수 방지는 보장되지 않는다. 모델 추론값을 백테스트에 주입할 때 반드시 *추론 시점 ≤ 진입 시점 - 1일* 이어야 한다.

## 재학습 트리거 조건

다음 중 하나라도 만족하면 재학습 큐 enqueue (관리자 작업):
- 마지막 학습일로부터 7일 경과
- 직전 30일 검증 정확도가 baseline 대비 5%p 이상 하락
- 모델 버전이 mock-* (초기 배포)
- 피처 정의 변경 (코드/지표 추가)

## 사용 예 (개발/CI)

torch / DB 미설치 환경에서도 합성 데이터로 검증:

```bash
export ML_USE_SYNTHETIC=true
pytest tests/unit/test_ml_engine.py
```

`tests/unit/test_ml_engine.py` 는 dataset 윈도잉, 모델 forward, 1 epoch 학습 후 loss 감소, 추론 결과 형식을 모두 검증한다.
