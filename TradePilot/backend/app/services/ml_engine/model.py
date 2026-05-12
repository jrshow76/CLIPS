"""LSTM 분류 모델.

구조 (CPU 친화적 소형 모델):
    Linear(n_features → hidden)
    LSTM(hidden, hidden, num_layers=2, dropout=0.2)
    LayerNorm(hidden)
    Linear(hidden → 3)

마지막 timestep 의 hidden 출력을 분류 헤드로 보낸다.
파라미터 수 (hidden=64, features=8): 약 50K 개. 모델 파일 < 1MB.

torch 미설치 환경에서도 모듈 import 단계는 통과하도록 lazy import 패턴 사용.
실제 모델 인스턴스화는 `build_model(config)` 로만 가능.
"""
from __future__ import annotations

from typing import Any

from app.services.ml_engine.config import MLConfig


def _import_torch():
    """torch lazy import."""
    try:
        import torch
        import torch.nn as nn
        return torch, nn
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "PyTorch 가 설치되어 있지 않습니다. ML 학습/추론 기능은 비활성화됩니다."
        ) from e


def build_model(config: MLConfig) -> Any:
    """MLConfig 로부터 LSTMClassifier 인스턴스를 생성한다."""
    torch, nn = _import_torch()

    class LSTMClassifier(nn.Module):
        """LSTM 3-class 분류기."""

        def __init__(
            self,
            n_features: int,
            hidden_size: int,
            num_layers: int,
            num_classes: int,
            dropout: float,
        ) -> None:
            super().__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers

            # 입력 임베딩 (피처 → hidden 차원 매핑)
            self.input_proj = nn.Linear(n_features, hidden_size)

            # 다층 LSTM
            self.lstm = nn.LSTM(
                input_size=hidden_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0.0,
            )
            self.layer_norm = nn.LayerNorm(hidden_size)
            self.dropout = nn.Dropout(dropout)
            self.head = nn.Linear(hidden_size, num_classes)

        def forward(self, x):  # x: (batch, lookback, n_features)
            h = self.input_proj(x)               # (batch, lookback, hidden)
            out, _ = self.lstm(h)                # (batch, lookback, hidden)
            last = out[:, -1, :]                 # (batch, hidden) - 마지막 timestep
            last = self.layer_norm(last)
            last = self.dropout(last)
            logits = self.head(last)             # (batch, num_classes)
            return logits

    model = LSTMClassifier(
        n_features=config.num_features,
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        num_classes=config.num_classes,
        dropout=config.dropout,
    )
    # 재현성을 위해 seed 적용
    torch.manual_seed(config.seed)
    return model


def count_parameters(model: Any) -> int:
    """학습 가능한 파라미터 수 (모델 사이즈 추정용)."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
