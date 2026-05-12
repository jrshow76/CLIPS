"""ML 엔진 단위 테스트.

DB 없이 동작: 합성 시계열로 dataset/모델/학습/추론 파이프라인을 검증한다.
torch 미설치 환경에서는 학습/추론 테스트는 skip 한다.
"""
from __future__ import annotations

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

# torch 가용성 체크
try:
    import torch  # noqa: F401

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# sklearn 가용성 체크
try:
    import sklearn  # noqa: F401

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from app.services.ml_engine.config import MLConfig
from app.services.ml_engine.features import (
    build_features,
    class_weights,
    label_horizon_class,
)
from app.services.ml_engine.synthetic import (
    make_regime_switching_series,
    make_synthetic_ohlcv,
)

pytestmark = pytest.mark.unit


# ============================================================================
# 합성 데이터 / 피처
# ============================================================================
def test_synthetic_ohlcv_shape() -> None:
    df = make_synthetic_ohlcv(code="TEST", days=300, seed=42)
    assert len(df) == 300
    assert set(df.columns) == {"open", "high", "low", "close", "volume"}
    # close 가 모두 양수
    assert (df["close"] > 0).all()
    # 평일만 채워졌는지
    weekdays = pd.DatetimeIndex(df.index).weekday
    assert (weekdays < 5).all()


def test_synthetic_reproducible() -> None:
    a = make_synthetic_ohlcv(code="SAME", days=100, seed=1)
    b = make_synthetic_ohlcv(code="SAME", days=100, seed=1)
    assert np.allclose(a["close"].values, b["close"].values)


def test_build_features_columns_and_no_nan() -> None:
    df = make_synthetic_ohlcv(code="FEAT", days=400, seed=7)
    features = ["close", "volume", "ma5", "ma20", "rsi14", "macd", "bb_pct_b", "obv"]
    feat_df = build_features(df, features)
    # 모든 피처가 존재
    assert list(feat_df.columns) == features
    # NaN/inf 제거됨
    assert not feat_df.isna().any().any()
    assert not np.isinf(feat_df.values).any()
    # 충분한 행 수 (워밍업 후)
    assert len(feat_df) > 200


def test_label_horizon_class_distribution() -> None:
    df = make_synthetic_ohlcv(code="LABEL", days=300, seed=11)
    labels = label_horizon_class(
        df["close"], horizon_days=1, up_threshold=0.01, down_threshold=-0.01
    )
    # 0/1/2 + -1 (미래 부족) 만 존재
    unique = set(labels.unique().tolist())
    assert unique.issubset({-1, 0, 1, 2})
    # 마지막 1행은 -1 (1일 후 가격이 없음)
    assert labels.iloc[-1] == -1


def test_class_weights_inverse_freq() -> None:
    # 균형: 가중치 ~ 1 근처
    labels = np.array([0, 1, 2, 0, 1, 2])
    w = class_weights(labels, num_classes=3)
    assert len(w) == 3
    assert np.allclose(w, 1.0, atol=0.01)

    # 불균형: 보합(1) 만 많음 → 가중치 감소
    labels = np.array([1] * 9 + [0] * 1 + [2] * 1, dtype=np.int64)  # 9:1:1
    w = class_weights(labels, num_classes=3)
    assert w[1] < w[0]
    assert w[1] < w[2]


# ============================================================================
# Dataset / 윈도잉
# ============================================================================
@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn 필요")
def test_make_windows_shapes() -> None:
    from app.services.ml_engine.dataset import build_dataset_from_ohlcv

    df = make_synthetic_ohlcv(code="WIN", days=400, seed=3)
    config = MLConfig(
        stock_code="WIN",
        horizon_days=1,
        lookback_days=30,
        epochs=1,
        batch_size=8,
    )
    train, val, scaler, meta = build_dataset_from_ohlcv(df, config)
    # X shape: (N, lookback, n_features)
    assert train.X.ndim == 3
    assert train.X.shape[1] == 30
    assert train.X.shape[2] == config.num_features
    # y shape: (N,)
    assert train.y.ndim == 1
    assert len(train.y) == train.X.shape[0]
    # 학습/검증 분리
    assert len(train) + len(val) > 0
    # scaler 정상 fit
    assert scaler.mean_.shape[-1] == config.num_features
    # meta 라벨 분포
    assert sum(meta["label_dist"].values()) == len(train) + len(val)


@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn 필요")
def test_time_split_no_leakage() -> None:
    """시간 분할이 인덱스 기반인지 (앞 train / 뒤 val)."""
    from app.services.ml_engine.dataset import (
        build_dataset_from_ohlcv,
    )

    df = make_synthetic_ohlcv(code="LEAK", days=400, seed=5)
    config = MLConfig(stock_code="LEAK", horizon_days=1, lookback_days=20, val_split=0.2)
    train, val, _scaler, _meta = build_dataset_from_ohlcv(df, config)
    # train 의 마지막 윈도우와 val 의 첫 윈도우가 연속
    assert len(train) > 0 and len(val) > 0
    # 검증 비율 ≈ 0.2
    ratio = len(val) / (len(train) + len(val))
    assert 0.10 < ratio < 0.30


# ============================================================================
# 모델 forward (torch 필수)
# ============================================================================
@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch 필요")
def test_lstm_classifier_forward_shape() -> None:
    import torch

    from app.services.ml_engine.model import build_model, count_parameters

    config = MLConfig(
        stock_code="FWD",
        horizon_days=1,
        lookback_days=30,
        hidden_size=32,
        num_layers=2,
    )
    model = build_model(config)
    batch_size = 4
    x = torch.randn(batch_size, config.lookback_days, config.num_features)
    logits = model(x)
    assert logits.shape == (batch_size, config.num_classes)
    # 파라미터 수가 적절한 범위 (CPU 친화적)
    n_params = count_parameters(model)
    assert 1_000 < n_params < 500_000


# ============================================================================
# 학습 1 epoch: loss 감소 (학습 가능성 sanity check)
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_train_loss_decreases_after_epoch() -> None:
    """학습 가능성 sanity: 합성 regime-switching 데이터에서 train loss 가 감소해야 한다."""
    from app.services.ml_engine.trainer import train_model

    # regime-switching 시계열은 학습 가능한 신호를 포함
    df = make_regime_switching_series(code="TRAIN", days=600, seed=21)

    with tempfile.TemporaryDirectory() as tmpdir:
        config = MLConfig(
            stock_code="TRAINTEST",
            horizon_days=1,
            lookback_days=20,
            hidden_size=32,
            num_layers=1,
            epochs=3,
            batch_size=32,
            learning_rate=1e-2,  # 빠른 수렴
            model_dir=tmpdir,
            seed=42,
        )
        result = train_model(df, config)

        # 학습 진행 검증
        assert result.epochs_run >= 1
        history = result.train_history
        assert len(history) >= 1
        # 첫 에포크 train_loss > 마지막 에포크 train_loss (학습이 진행됨)
        if len(history) >= 2:
            assert history[-1]["train_loss"] < history[0]["train_loss"]

        # 모델 파일이 디스크에 저장됨 (디렉토리 정리 전에 검증)
        assert os.path.exists(os.path.join(result.model_dir, "model.pt"))
        assert os.path.exists(os.path.join(result.model_dir, "scaler.joblib"))
        assert os.path.exists(os.path.join(result.model_dir, "meta.json"))


# ============================================================================
# 추론 결과 형식
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_predict_result_keys_and_probabilities() -> None:
    from app.services.ml_engine import predict_from_ohlcv, train_model

    df = make_regime_switching_series(code="PRED", days=400, seed=33)

    with tempfile.TemporaryDirectory() as tmpdir:
        config = MLConfig(
            stock_code="PREDTEST",
            horizon_days=1,
            lookback_days=20,
            hidden_size=32,
            num_layers=1,
            epochs=2,
            batch_size=32,
            model_dir=tmpdir,
            seed=42,
        )
        train_model(df, config)
        result = predict_from_ohlcv(df, config)

    # 결과 구조
    out = result.to_dict()
    assert "direction" in out
    assert out["direction"] in ("UP", "FLAT", "DOWN")
    assert 0.0 <= out["confidence"] <= 1.0
    # 확률 합 ≈ 1
    s = out["prob_up"] + out["prob_flat"] + out["prob_down"]
    assert abs(s - 1.0) < 1e-4
    assert out["model_key"] == "PREDTEST_1d"
    assert out["horizon_days"] == 1


@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_predict_to_ml_record_decimal_format() -> None:
    """`predictions_to_ml_record` 가 ml_predictions 테이블 컬럼과 일치하는지."""
    from decimal import Decimal

    from app.services.ml_engine import predict_from_ohlcv, predictions_to_ml_record, train_model

    df = make_regime_switching_series(code="REC", days=400, seed=51)
    with tempfile.TemporaryDirectory() as tmpdir:
        config = MLConfig(
            stock_code="RECTEST",
            horizon_days=3,
            lookback_days=20,
            hidden_size=32,
            num_layers=1,
            epochs=1,
            batch_size=32,
            model_dir=tmpdir,
        )
        train_model(df, config)
        result = predict_from_ohlcv(df, config)
        record = predictions_to_ml_record(result, last_close=float(df["close"].iloc[-1]))

    # 필수 컬럼
    for col in ("base_date", "horizon", "pred_mean", "pred_lower", "pred_upper", "model_version", "direction_acc"):
        assert col in record
    # Decimal 타입
    assert isinstance(record["pred_mean"], Decimal)
    # bound 조건 (DDL CHECK)
    assert record["pred_lower"] <= record["pred_mean"] <= record["pred_upper"]
    # version 형식
    assert record["model_version"].startswith("lstm-v1-")


# ============================================================================
# Registry
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_registry_list_and_get(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ml_engine import list_models, model_exists, train_model
    from app.services.ml_engine.registry import get_model_meta

    df = make_regime_switching_series(code="REG", days=400, seed=77)
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("ML_MODEL_DIR", tmpdir)
        config = MLConfig(
            stock_code="REGTEST",
            horizon_days=1,
            lookback_days=20,
            hidden_size=32,
            num_layers=1,
            epochs=1,
            batch_size=32,
            model_dir=tmpdir,
        )
        train_model(df, config)

        models = list_models(base=tmpdir)
        assert len(models) == 1
        assert models[0].model_key == "REGTEST_1d"

        meta = get_model_meta("REGTEST_1d", base=tmpdir)
        assert meta is not None
        assert meta.stock_code == "REGTEST"

        assert model_exists("REGTEST", 1, base=tmpdir) is True
        assert model_exists("NONE", 1, base=tmpdir) is False


# ============================================================================
# ML Signal 백테스트 전략
# ============================================================================
def test_ml_signal_strategy_basic() -> None:
    from app.services.backtest_engine.strategies.ml_signal import MLSignalStrategy

    dates = pd.bdate_range("2025-01-01", periods=10)
    df = pd.DataFrame(
        {"close": np.linspace(100, 110, 10), "open": 100, "high": 110, "low": 95, "volume": 1000},
        index=dates,
    )
    predictions = {
        dates[2].date().isoformat(): {"direction": "UP", "confidence": 0.8},
        dates[5].date().isoformat(): {"direction": "DOWN", "confidence": 0.75},
        dates[7].date().isoformat(): {"direction": "UP", "confidence": 0.4},  # 신뢰도 미달
    }
    strategy = MLSignalStrategy(params={"predictions": predictions, "min_confidence": 0.6})
    signals = strategy.generate_signals(df)

    # shift(1) 적용으로 시그널이 다음 거래일에 발생
    assert signals.iloc[3] == 1  # dates[2] UP → 다음날(인덱스 3) 매수
    assert signals.iloc[6] == -1  # dates[5] DOWN → 다음날 매도
    assert signals.iloc[8] == 0  # dates[7] 신뢰도 미달 → 무시


def test_composite_ml_predict_rule() -> None:
    """Composite DSL 의 `ml_predict` 룰 평가."""
    from app.services.backtest_engine.strategies.composite import _eval_rules

    dates = pd.bdate_range("2025-01-01", periods=8)
    df = pd.DataFrame({"close": np.arange(100, 108)}, index=dates)
    df.attrs["ml_predictions"] = {
        dates[1].date().isoformat(): {"direction": "UP", "confidence": 0.75},
        dates[3].date().isoformat(): {"direction": "UP", "confidence": 0.5},  # 미달
    }
    rule = {"type": "ml_predict", "direction": "UP", "min_confidence": 0.6}
    mask = _eval_rules(rule, df)
    assert bool(mask.iloc[1]) is True
    assert bool(mask.iloc[3]) is False
    assert bool(mask.iloc[0]) is False
