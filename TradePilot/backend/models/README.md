# TradePilot ML 모델 저장소

런타임에 학습된 LSTM 모델 파일이 저장되는 디렉토리.

## 구조

```
backend/models/
├── .gitkeep                      # 디렉토리 트래킹용
├── README.md                     # 본 문서
└── {stock_code}_{horizon}d/      # 모델 단위 디렉토리
    ├── model.pt                  # PyTorch state_dict (best epoch)
    ├── scaler.joblib             # StandardScaler (학습 데이터로 fit)
    └── meta.json                 # 피처/하이퍼/학습 메트릭/이력
```

예시:
- `005930_1d/`  - 삼성전자(005930) 1일 호라이즌
- `005930_3d/`  - 삼성전자 3일
- `000660_5d/`  - SK하이닉스 5일

## 파일 정책

- 모델 파일(`*.pt`, `*.joblib`, `meta.json`)은 **Git 추적 대상이 아님**
  (루트 `.gitignore` 의 `models/`, `*.pt`, `*.joblib` 규칙으로 제외)
- 학습 시 동일 키 디렉토리가 있으면 **덮어쓰기**됨 (이전 모델 백업이 필요하면 별도 작업으로 처리)

## 운영 디렉토리 변경

환경변수 `ML_MODEL_DIR` 로 오버라이드 가능. 예:
```
ML_MODEL_DIR=/var/lib/tradepilot/models
```

기본값은 `app.core.config.settings.ML_MODEL_DIR` (`/var/lib/tradepilot/models`)이며,
개발/테스트 환경에서는 본 디렉토리(`backend/models`) 사용을 권장한다.

## 정리 정책

- 30일 이상 추론 호출이 없는 모델은 운영 배치로 아카이브한다.
- 동일 종목/호라이즌의 모델 버전 이력은 `tp_analysis.ml_predictions.model_version` 컬럼으로 추적한다.
