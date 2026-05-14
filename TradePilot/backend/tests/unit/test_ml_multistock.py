"""ML 멀티 종목 모델 단위 테스트.

테스트 범위:
    - MultiStockLSTMClassifier / SectorLSTMClassifier forward shape
    - 종목 임베딩이 다른 값을 학습하는지 (수렴 sanity)
    - 섹터 모델 학습 → 베이스라인 대비 정확도 향상
    - 앙상블 결과 형식 / 정규화
    - registry: get_model_for_stock 우선순위
"""
from __future__ import annotations

import os
import tempfile
import time

import numpy as np
import pandas as pd
import pytest

try:
    import torch  # noqa: F401

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import sklearn  # noqa: F401

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from app.services.ml_engine.config import MLConfig
from app.services.ml_engine.synthetic import (
    make_regime_switching_series,
    make_synthetic_ohlcv,
)

pytestmark = pytest.mark.unit


# ============================================================================
# 모델 forward shape
# ============================================================================
@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch 필요")
def test_sector_lstm_forward_shape() -> None:
    import torch as _torch

    from app.services.ml_engine.model import build_sector_model, count_parameters

    config = MLConfig(
        stock_code="SECTOR_TEST",
        horizon_days=1,
        lookback_days=20,
        hidden_size=32,
        num_layers=1,
    )
    model = build_sector_model(config)
    batch_size = 4
    x = _torch.randn(batch_size, config.lookback_days, config.num_features)
    logits = model(x)
    assert logits.shape == (batch_size, config.num_classes)

    # 임베딩이 없으므로 단일 모델과 유사한 크기
    n_params = count_parameters(model)
    assert 1_000 < n_params < 500_000


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch 필요")
def test_multistock_lstm_forward_shape() -> None:
    """글로벌 모델 forward shape + 임베딩 차원."""
    import torch as _torch

    from app.services.ml_engine.model import (
        build_multistock_model,
        count_parameters,
    )

    config = MLConfig(
        stock_code="GLOBAL_TEST",
        horizon_days=1,
        lookback_days=20,
        hidden_size=32,
        num_layers=1,
    )
    num_stocks = 10
    model = build_multistock_model(config, num_stocks=num_stocks, embed_dim=8)

    batch_size = 4
    x = _torch.randn(batch_size, config.lookback_days, config.num_features)
    sids = _torch.tensor([0, 1, 5, 7], dtype=_torch.long)
    logits = model(x, sids)
    assert logits.shape == (batch_size, config.num_classes)

    # 임베딩 weight 가 학습 대상에 포함
    assert hasattr(model, "stock_embedding")
    assert model.stock_embedding.weight.shape == (num_stocks, 8)

    # 모델 크기 < 10MB (글로벌도 작아야 함)
    n_params = count_parameters(model)
    # 파라미터 4 byte 가정 → < 2.5M 파라미터 ⇒ < 10MB
    assert n_params < 2_500_000


@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch 필요")
def test_multistock_embedding_distinguishes_stocks() -> None:
    """종목 임베딩이 학습 가능한지 (gradient 가 다른 종목별로 다르게 전파)."""
    import torch as _torch

    from app.services.ml_engine.model import build_multistock_model

    config = MLConfig(
        stock_code="X",
        horizon_days=1,
        lookback_days=10,
        hidden_size=16,
        num_layers=1,
    )
    model = build_multistock_model(config, num_stocks=5, embed_dim=4)

    # 같은 시계열, 다른 종목 ID → 다른 출력
    x = _torch.randn(2, config.lookback_days, config.num_features)
    sids_a = _torch.tensor([0, 0], dtype=_torch.long)
    sids_b = _torch.tensor([3, 3], dtype=_torch.long)

    with _torch.no_grad():
        logits_a = model(x, sids_a)
        logits_b = model(x, sids_b)

    # 임베딩 weight 가 무작위로 초기화되므로 서로 다른 결과여야 함
    diff = (logits_a - logits_b).abs().sum().item()
    assert diff > 1e-5, "종목 임베딩이 다른 종목에 대해 동일한 출력을 내고 있습니다"


# ============================================================================
# 데이터셋 통합
# ============================================================================
@pytest.mark.skipif(not HAS_SKLEARN, reason="scikit-learn 필요")
def test_build_multistock_dataset_shapes() -> None:
    from app.services.ml_engine.dataset import build_multistock_dataset_from_ohlcvs

    codes = ["A001", "A002", "A003"]
    ohlcv_by_code = {
        code: make_regime_switching_series(code=code, days=300, seed=i + 1)
        for i, code in enumerate(codes)
    }
    config = MLConfig(
        stock_code="multi",
        horizon_days=1,
        lookback_days=20,
        epochs=1,
        batch_size=16,
    )
    train, val, scaler, stock_to_id, meta = build_multistock_dataset_from_ohlcvs(
        ohlcv_by_code, config, use_sample_weight=True
    )

    assert train.X.ndim == 3
    assert train.X.shape[1] == 20
    assert train.X.shape[2] == config.num_features
    assert len(train.y) == train.X.shape[0]
    assert len(train.stock_ids) == train.X.shape[0]
    assert set(stock_to_id.keys()) == set(codes)
    assert meta["n_stocks"] == 3
    # 샘플 가중치는 평균 약 1
    assert train.sample_weights is not None
    assert 0.5 < float(train.sample_weights.mean()) < 2.0


# ============================================================================
# 섹터 모델 학습 + 베이스라인 비교
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_train_sector_model_converges_and_beats_baseline() -> None:
    """섹터 모델 학습 결과 정확도가 베이스라인(33%) 이상이어야 한다."""
    from app.services.ml_engine import train_sector_model

    codes = ["S001", "S002", "S003", "S004"]
    ohlcv_by_code = {
        code: make_regime_switching_series(code=code, days=400, seed=10 + i)
        for i, code in enumerate(codes)
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        config = MLConfig(
            stock_code="SECTOR_X",
            horizon_days=1,
            lookback_days=20,
            hidden_size=32,
            num_layers=1,
            epochs=4,
            batch_size=32,
            learning_rate=5e-3,
            model_dir=tmpdir,
            seed=42,
        )
        result = train_sector_model(
            sector_code="SEMI",
            ohlcv_by_code=ohlcv_by_code,
            config=config,
            model_dir_base=tmpdir,
        )

        # 학습 진행 확인
        assert result.epochs_run >= 1
        assert result.model_kind == "SECTOR"
        assert result.n_stocks == 4
        # 베이스라인(균등 33%) 이상이어야 함 - 합성 regime 데이터는 패턴이 강함
        assert result.best_val_acc >= 0.30
        # 저장 확인
        assert os.path.exists(os.path.join(result.model_dir, "model.pt"))
        assert os.path.exists(os.path.join(result.model_dir, "scaler.joblib"))
        # 종목별 정확도 기록
        assert isinstance(result.per_stock_val_acc, dict)


# ============================================================================
# 글로벌 모델 학습
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_train_global_model_with_embeddings() -> None:
    """글로벌 모델이 종목 임베딩과 함께 정상 학습된다."""
    from app.services.ml_engine import train_multistock_model

    codes = [f"G{i:03d}" for i in range(6)]
    ohlcv_by_code = {
        code: make_regime_switching_series(code=code, days=300, seed=50 + i)
        for i, code in enumerate(codes)
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        config = MLConfig(
            stock_code="global",
            horizon_days=1,
            lookback_days=20,
            hidden_size=32,
            num_layers=1,
            epochs=2,
            batch_size=32,
            learning_rate=5e-3,
            model_dir=tmpdir,
            seed=42,
        )
        result = train_multistock_model(
            ohlcv_by_code=ohlcv_by_code,
            config=config,
            model_dir_base=tmpdir,
        )
        assert result.model_kind == "GLOBAL"
        assert result.n_stocks == 6
        assert os.path.exists(os.path.join(result.model_dir, "meta.json"))


# ============================================================================
# Registry: 모델 선택 우선순위
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_get_model_for_stock_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """개별 → 섹터 → 글로벌 우선순위 검증."""
    from app.services.ml_engine import (
        ModelKind,
        get_model_for_stock,
        train_model,
        train_multistock_model,
        train_sector_model,
    )

    code = "PRIO001"
    sector = "TECH"

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("ML_MODEL_DIR", tmpdir)

        # 1) 글로벌만 있는 상태
        global_ohlcv = {
            f"G{i:03d}": make_regime_switching_series(code=f"G{i:03d}", days=200, seed=i)
            for i in range(3)
        }
        global_ohlcv[code] = make_regime_switching_series(code=code, days=200, seed=99)
        cfg_g = MLConfig(
            stock_code="global", horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_multistock_model(global_ohlcv, cfg_g, model_dir_base=tmpdir)
        m = get_model_for_stock(code, 1, sector_code=sector, base=tmpdir)
        assert m is not None
        assert m.kind == ModelKind.GLOBAL

        # 2) 섹터 추가
        sec_ohlcv = {
            f"S{i:03d}": make_regime_switching_series(code=f"S{i:03d}", days=200, seed=10 + i)
            for i in range(3)
        }
        cfg_s = MLConfig(
            stock_code=sector, horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_sector_model(sector, sec_ohlcv, cfg_s, model_dir_base=tmpdir)
        m = get_model_for_stock(code, 1, sector_code=sector, base=tmpdir)
        assert m is not None
        assert m.kind == ModelKind.SECTOR

        # 3) 개별 추가 (fresh)
        ind_ohlcv = make_regime_switching_series(code=code, days=300, seed=99)
        cfg_i = MLConfig(
            stock_code=code, horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_model(ind_ohlcv, cfg_i)
        m = get_model_for_stock(code, 1, sector_code=sector, base=tmpdir)
        assert m is not None
        assert m.kind == ModelKind.INDIVIDUAL


# ============================================================================
# 앙상블 결과 형식
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_predict_ensemble_shape_and_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    """앙상블 결과의 형식, 확률 합 ≈ 1, used_kinds 채워짐."""
    from app.services.ml_engine import (
        predict_ensemble,
        train_model,
        train_multistock_model,
        train_sector_model,
    )

    code = "ENS001"
    sector = "FIN"

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("ML_MODEL_DIR", tmpdir)

        # 글로벌 모델
        global_ohlcv = {
            code: make_regime_switching_series(code=code, days=200, seed=111),
            "OTH1": make_regime_switching_series(code="OTH1", days=200, seed=112),
            "OTH2": make_regime_switching_series(code="OTH2", days=200, seed=113),
        }
        cfg_g = MLConfig(
            stock_code="global", horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_multistock_model(global_ohlcv, cfg_g, model_dir_base=tmpdir)

        # 섹터 모델
        sec_ohlcv = {
            code: make_regime_switching_series(code=code, days=200, seed=111),
            "FIN1": make_regime_switching_series(code="FIN1", days=200, seed=114),
        }
        cfg_s = MLConfig(
            stock_code=sector, horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_sector_model(sector, sec_ohlcv, cfg_s, model_dir_base=tmpdir)

        # 개별 모델
        ind_ohlcv = make_regime_switching_series(code=code, days=300, seed=111)
        cfg_i = MLConfig(
            stock_code=code, horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_model(ind_ohlcv, cfg_i)

        # 앙상블 추론
        result = predict_ensemble(
            ohlcv=ind_ohlcv,
            stock_code=code,
            horizon=1,
            sector_code=sector,
            base=tmpdir,
        )

        # 결과 형식
        d = result.to_dict()
        assert d["direction"] in ("UP", "FLAT", "DOWN")
        assert 0.0 <= d["confidence"] <= 1.0
        s = d["prob_up"] + d["prob_flat"] + d["prob_down"]
        assert abs(s - 1.0) < 1e-4
        # 3가지 모두 기여
        assert set(result.used_kinds) == {"INDIVIDUAL", "SECTOR", "GLOBAL"}
        # contributions 형식 검증
        for k in ("INDIVIDUAL", "SECTOR", "GLOBAL"):
            contrib = result.contributions[k]
            assert "model_key" in contrib
            assert 0.0 <= contrib["weight"] <= 1.0
            ssum = contrib["prob_up"] + contrib["prob_flat"] + contrib["prob_down"]
            assert abs(ssum - 1.0) < 1e-3

        # 가중치 합 ≈ 1
        total_w = sum(c["weight"] for c in result.contributions.values())
        assert abs(total_w - 1.0) < 1e-4


@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_predict_ensemble_no_individual_fallback_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    """개별 모델이 없으면 자동으로 (SECTOR:0.6, GLOBAL:0.4) 가중치 적용."""
    from app.services.ml_engine import (
        predict_ensemble,
        train_multistock_model,
        train_sector_model,
    )

    code = "NIN001"
    sector = "BIO"

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("ML_MODEL_DIR", tmpdir)

        global_ohlcv = {
            f"X{i}": make_regime_switching_series(code=f"X{i}", days=200, seed=300 + i)
            for i in range(3)
        }
        cfg_g = MLConfig(
            stock_code="global", horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_multistock_model(global_ohlcv, cfg_g, model_dir_base=tmpdir)

        sec_ohlcv = {
            code: make_regime_switching_series(code=code, days=200, seed=400),
            "BIO1": make_regime_switching_series(code="BIO1", days=200, seed=401),
        }
        cfg_s = MLConfig(
            stock_code=sector, horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        )
        train_sector_model(sector, sec_ohlcv, cfg_s, model_dir_base=tmpdir)

        ohlcv = make_regime_switching_series(code=code, days=200, seed=400)
        result = predict_ensemble(
            ohlcv=ohlcv,
            stock_code=code,
            horizon=1,
            sector_code=sector,
            base=tmpdir,
        )
        assert set(result.used_kinds) == {"SECTOR", "GLOBAL"}
        # 기본 가중치 검증
        assert abs(result.contributions["SECTOR"]["weight"] - 0.6) < 1e-4
        assert abs(result.contributions["GLOBAL"]["weight"] - 0.4) < 1e-4


# ============================================================================
# Catalog
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_list_available_models_groups_by_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.ml_engine import (
        list_available_models,
        train_model,
        train_multistock_model,
        train_sector_model,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("ML_MODEL_DIR", tmpdir)

        # 개별
        ind_ohlcv = make_regime_switching_series(code="IND1", days=200, seed=1)
        train_model(ind_ohlcv, MLConfig(
            stock_code="IND1", horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        ))

        # 섹터
        sec_ohlcv = {
            f"SEC{i}": make_regime_switching_series(code=f"SEC{i}", days=200, seed=10 + i)
            for i in range(2)
        }
        train_sector_model("TECH", sec_ohlcv, MLConfig(
            stock_code="TECH", horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        ), model_dir_base=tmpdir)

        # 글로벌
        glo_ohlcv = {
            f"GLO{i}": make_regime_switching_series(code=f"GLO{i}", days=200, seed=20 + i)
            for i in range(2)
        }
        train_multistock_model(glo_ohlcv, MLConfig(
            stock_code="global", horizon_days=1, lookback_days=15,
            hidden_size=16, num_layers=1, epochs=1, batch_size=32,
            model_dir=tmpdir,
        ), model_dir_base=tmpdir)

        grouped = list_available_models(base=tmpdir)
        assert len(grouped["INDIVIDUAL"]) >= 1
        assert len(grouped["SECTOR"]) >= 1
        assert len(grouped["GLOBAL"]) >= 1
        # 키 패턴 확인
        assert any(it["model_key"] == "IND1_1d" for it in grouped["INDIVIDUAL"])
        assert any(it["model_key"] == "sector_TECH_1d" for it in grouped["SECTOR"])
        assert any(it["model_key"] == "global_1d" for it in grouped["GLOBAL"])


# ============================================================================
# 백테스트 ml_signal ensemble 옵션
# ============================================================================
def test_ml_signal_strategy_ensemble_option() -> None:
    """ensemble=True 면 ensemble_predictions 키 우선 사용."""
    from app.services.backtest_engine.strategies.ml_signal import MLSignalStrategy

    dates = pd.bdate_range("2025-01-01", periods=6)
    df = pd.DataFrame(
        {"close": np.arange(100, 106), "open": 100, "high": 110, "low": 95, "volume": 1000},
        index=dates,
    )
    base_pred = {
        dates[1].date().isoformat(): {"direction": "UP", "confidence": 0.9},
    }
    ensemble_pred = {
        dates[1].date().isoformat(): {"direction": "DOWN", "confidence": 0.9},
    }
    strategy = MLSignalStrategy(params={
        "predictions": base_pred,
        "ensemble_predictions": ensemble_pred,
        "ensemble": True,
        "min_confidence": 0.5,
    })
    signals = strategy.generate_signals(df)
    # ensemble_predictions 의 DOWN → shift(1) 이후 매도(-1)
    assert signals.iloc[2] == -1


def test_eval_ml_predict_rule_ensemble_attr() -> None:
    """Composite DSL: ensemble=true 면 ml_ensemble_predictions 우선."""
    from app.services.backtest_engine.strategies.ml_signal import (
        eval_ml_predict_rule,
    )

    dates = pd.bdate_range("2025-01-01", periods=5)
    df = pd.DataFrame({"close": np.arange(100, 105)}, index=dates)
    df.attrs["ml_predictions"] = {
        dates[1].date().isoformat(): {"direction": "DOWN", "confidence": 0.9}
    }
    df.attrs["ml_ensemble_predictions"] = {
        dates[1].date().isoformat(): {"direction": "UP", "confidence": 0.9}
    }
    rule = {
        "type": "ml_predict",
        "direction": "UP",
        "min_confidence": 0.6,
        "ensemble": True,
    }
    mask = eval_ml_predict_rule(rule, df)
    assert bool(mask.iloc[1]) is True


# ============================================================================
# 학습 시간 측정 (성능 sanity)
# ============================================================================
@pytest.mark.skipif(not (HAS_TORCH and HAS_SKLEARN), reason="torch + sklearn 필요")
def test_global_training_time_budget() -> None:
    """소규모 글로벌 모델은 CPU 에서도 1분 이내 학습 완료해야 한다 (sanity)."""
    from app.services.ml_engine import train_multistock_model

    codes = [f"P{i:03d}" for i in range(8)]
    ohlcv_by_code = {
        code: make_synthetic_ohlcv(code=code, days=200, seed=500 + i)
        for i, code in enumerate(codes)
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        config = MLConfig(
            stock_code="global",
            horizon_days=1,
            lookback_days=15,
            hidden_size=16,
            num_layers=1,
            epochs=2,
            batch_size=64,
            model_dir=tmpdir,
        )
        start = time.time()
        result = train_multistock_model(ohlcv_by_code, config, model_dir_base=tmpdir)
        elapsed = time.time() - start
        # 소규모 합성 데이터 학습은 60초 이내 완료
        assert elapsed < 60.0
        assert result.duration_sec < 60.0
