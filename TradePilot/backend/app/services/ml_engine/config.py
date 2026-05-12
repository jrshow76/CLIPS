"""ML 엔진 설정 데이터클래스.

`MLConfig` 는 학습/추론 전 과정에서 공유되는 하이퍼파라미터와 운영 파라미터를
한 곳에 모아둔다. 백테스트 엔진의 `BacktestConfig` 와 동일한 스타일을 따른다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

# 기본 피처 (시계열 누수 우려가 없는 것만 포함)
DEFAULT_FEATURES: tuple[str, ...] = (
    "close",        # 종가 (log return 으로 변환)
    "volume",       # 거래량 (z-score 정규화 후 사용)
    "ma5",          # 단기 이동평균 비 (close 대비)
    "ma20",         # 중기 이동평균 비
    "rsi14",        # RSI
    "macd",         # MACD
    "bb_pct_b",     # Bollinger %B
    "obv",          # OBV (z-score 정규화)
)

# 3-class 임계값 (수익률 기준): 상승 / 보합 / 하락
DEFAULT_UP_THRESHOLD: float = 0.01     # +1% 이상 상승
DEFAULT_DOWN_THRESHOLD: float = -0.01  # -1% 미만 하락


@dataclass
class MLConfig:
    """ML 학습/추론 설정."""

    # ----------------------------------------------------------------
    # 모델/입력 구조
    # ----------------------------------------------------------------
    lookback_days: int = 60                           # 입력 시퀀스 길이
    horizon_days: int = 1                             # 예측 기간 (1/3/5)
    features: list[str] = field(default_factory=lambda: list(DEFAULT_FEATURES))

    # ----------------------------------------------------------------
    # 클래스 라벨링
    # ----------------------------------------------------------------
    up_threshold: float = DEFAULT_UP_THRESHOLD
    down_threshold: float = DEFAULT_DOWN_THRESHOLD

    # ----------------------------------------------------------------
    # 학습 데이터/분할
    # ----------------------------------------------------------------
    train_start: date | None = None
    train_end: date | None = None
    val_split: float = 0.15                           # 시간 순서 기반 validation 비율

    # ----------------------------------------------------------------
    # 학습 하이퍼파라미터
    # ----------------------------------------------------------------
    batch_size: int = 64
    epochs: int = 30
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    hidden_size: int = 64
    num_layers: int = 2
    dropout: float = 0.2
    early_stopping_patience: int = 5

    # ----------------------------------------------------------------
    # 운영
    # ----------------------------------------------------------------
    stock_code: str = ""                              # 학습 대상 종목 (운영 식별자)
    model_dir: str = field(default_factory=lambda: os.getenv("ML_MODEL_DIR", "backend/models"))
    seed: int = 42
    device: str = "cpu"                               # 운영은 CPU 고정

    # ----------------------------------------------------------------
    # 메서드
    # ----------------------------------------------------------------
    @property
    def num_features(self) -> int:
        return len(self.features)

    @property
    def num_classes(self) -> int:
        # 3-class: 0=하락, 1=보합, 2=상승
        return 3

    @property
    def model_key(self) -> str:
        """모델 식별자. 종목코드+호라이즌 단위로 분리 저장."""
        code = self.stock_code or "unknown"
        return f"{code}_{self.horizon_days}d"

    def model_path(self, base: str | None = None) -> str:
        """저장 디렉토리 경로 (모델 키 단위)."""
        root = base or self.model_dir
        return os.path.join(root, self.model_key)
