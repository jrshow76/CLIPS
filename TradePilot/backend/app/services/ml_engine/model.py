"""LSTM 분류 모델.

기본 모델 (단일 종목):
    Linear(n_features → hidden)
    LSTM(hidden, hidden, num_layers=2, dropout=0.2)
    LayerNorm(hidden)
    Linear(hidden → 3)

마지막 timestep 의 hidden 출력을 분류 헤드로 보낸다.
파라미터 수 (hidden=64, features=8): 약 50K 개. 모델 파일 < 1MB.

멀티 종목 모델:
    - SectorLSTMClassifier: 단일 섹터 내 종목들이 같은 가중치 공유 (임베딩 없음)
    - MultiStockLSTMClassifier: 글로벌 모델. 종목 ID 를 학습 가능 임베딩으로 입력에 결합

torch 미설치 환경에서도 모듈 import 단계는 통과하도록 lazy import 패턴 사용.
실제 모델 인스턴스화는 `build_model(config)` / `build_sector_model(...)` /
`build_multistock_model(...)` 로만 가능.
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


def build_sector_model(config: MLConfig) -> Any:
    """섹터 공통 LSTM 모델.

    구조상 LSTMClassifier 와 동일하지만, 다중 종목 데이터를 학습한다.
    종목 임베딩이 없어 같은 섹터 내에서는 공통 패턴만 학습한다.
    파라미터 수가 단일 모델과 동일해 모델 크기가 작다.
    """
    torch, nn = _import_torch()

    class SectorLSTMClassifier(nn.Module):
        """섹터 단위 공통 LSTM 분류기 (임베딩 없음)."""

        def __init__(
            self,
            n_features: int,
            hidden_size: int,
            num_layers: int,
            num_classes: int,
            dropout: float,
        ) -> None:
            super().__init__()
            self.input_proj = nn.Linear(n_features, hidden_size)
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

        def forward(self, x, stock_ids=None):
            """forward.

            stock_ids 인자는 인터페이스 호환용 (섹터 모델은 사용하지 않는다).
            """
            _ = stock_ids
            h = self.input_proj(x)
            out, _hc = self.lstm(h)
            last = out[:, -1, :]
            last = self.layer_norm(last)
            last = self.dropout(last)
            logits = self.head(last)
            return logits

    model = SectorLSTMClassifier(
        n_features=config.num_features,
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        num_classes=config.num_classes,
        dropout=config.dropout,
    )
    torch.manual_seed(config.seed)
    return model


def build_multistock_model(config: MLConfig, num_stocks: int, embed_dim: int = 8) -> Any:
    """글로벌 멀티 종목 LSTM 모델 (종목 임베딩 포함).

    Args:
        config: MLConfig
        num_stocks: 학습 대상 종목 수 (임베딩 vocab 크기)
        embed_dim: 종목 임베딩 차원 (기본 8)

    구조:
        시계열 입력 (batch, lookback, n_features)
        종목 ID 입력 (batch,) → Embedding (batch, embed_dim) → broadcast
        concat → (batch, lookback, n_features + embed_dim)
        Linear → hidden → LSTM → 분류 헤드
    """
    torch, nn = _import_torch()

    class MultiStockLSTMClassifier(nn.Module):
        """종목 임베딩을 결합하는 글로벌 LSTM 분류기."""

        def __init__(
            self,
            n_features: int,
            hidden_size: int,
            num_layers: int,
            num_classes: int,
            dropout: float,
            num_stocks: int,
            embed_dim: int,
        ) -> None:
            super().__init__()
            self.num_stocks = num_stocks
            self.embed_dim = embed_dim
            self.n_features = n_features

            # 종목 임베딩
            self.stock_embedding = nn.Embedding(
                num_embeddings=num_stocks,
                embedding_dim=embed_dim,
            )
            # 입력 임베딩 (피처 + 종목 임베딩 → hidden)
            self.input_proj = nn.Linear(n_features + embed_dim, hidden_size)
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

        def forward(self, x, stock_ids):
            """forward.

            Args:
                x: (batch, lookback, n_features)
                stock_ids: (batch,) long tensor - 종목 인덱스
            """
            # 임베딩 → (batch, embed_dim)
            emb = self.stock_embedding(stock_ids)
            # broadcast → (batch, lookback, embed_dim)
            lookback = x.shape[1]
            emb_expanded = emb.unsqueeze(1).expand(-1, lookback, -1)
            # concat → (batch, lookback, n_features + embed_dim)
            combined = torch.cat([x, emb_expanded], dim=-1)
            h = self.input_proj(combined)
            out, _hc = self.lstm(h)
            last = out[:, -1, :]
            last = self.layer_norm(last)
            last = self.dropout(last)
            logits = self.head(last)
            return logits

    model = MultiStockLSTMClassifier(
        n_features=config.num_features,
        hidden_size=config.hidden_size,
        num_layers=config.num_layers,
        num_classes=config.num_classes,
        dropout=config.dropout,
        num_stocks=num_stocks,
        embed_dim=embed_dim,
    )
    torch.manual_seed(config.seed)
    return model


def count_parameters(model: Any) -> int:
    """학습 가능한 파라미터 수 (모델 사이즈 추정용)."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
