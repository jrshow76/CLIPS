"""학습 루프.

- 손실: CrossEntropyLoss (클래스 가중치 적용)
- 옵티마이저: AdamW
- 스케줄러: ReduceLROnPlateau (val_loss 기준)
- EarlyStopping: patience=config.early_stopping_patience
- 메트릭: accuracy, macro F1, confusion matrix

학습 산출물 저장 구조:
    {model_dir}/{stock_code}_{horizon}d/
        ├── model.pt       (state_dict)
        ├── scaler.joblib  (StandardScaler)
        └── meta.json      (피처/하이퍼/메트릭)
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
import structlog

from app.services.ml_engine.config import MLConfig
from app.services.ml_engine.dataset import (
    build_dataset_from_ohlcv,
    build_multistock_dataset_from_ohlcvs,
    make_loaders,
    make_multi_loaders,
)
from app.services.ml_engine.model import (
    build_model,
    build_multistock_model,
    build_sector_model,
    count_parameters,
)

log = structlog.get_logger(__name__)


@dataclass
class TrainResult:
    """학습 결과 요약."""

    model_key: str
    model_dir: str
    epochs_run: int
    best_val_loss: float
    best_val_acc: float
    best_val_f1: float
    train_history: list[dict[str, float]]
    confusion_matrix: list[list[int]]
    label_dist: dict[int, int]
    class_weights: list[float]
    duration_sec: float
    model_param_count: int
    finished_at: str  # ISO8601


def _import_torch():
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        return torch, nn, optim
    except ImportError as e:  # pragma: no cover
        raise ImportError("PyTorch 가 설치되어 있지 않습니다.") from e


def train_model(
    ohlcv: pd.DataFrame,
    config: MLConfig,
    progress_cb: Any = None,
) -> TrainResult:
    """학습 진입점.

    Args:
        ohlcv: OHLCV DataFrame (index=DatetimeIndex)
        config: MLConfig (stock_code 필수)
        progress_cb: Callable[[int], None] - 0~100 진행률

    Returns:
        TrainResult
    """
    torch, nn, optim = _import_torch()
    started = time.time()

    # 1) 데이터 준비
    _notify(progress_cb, 5)
    train_arr, val_arr, scaler, meta = build_dataset_from_ohlcv(ohlcv, config)
    if len(train_arr) == 0:
        raise ValueError("학습 데이터가 부족합니다. lookback/horizon 또는 입력 시계열 길이를 확인하세요.")
    log.info(
        "ml_dataset_built",
        n_train=len(train_arr),
        n_val=len(val_arr),
        n_features=config.num_features,
    )
    _notify(progress_cb, 15)

    train_loader, val_loader = make_loaders(train_arr, val_arr, batch_size=config.batch_size)

    # 2) 모델/옵티마이저
    device = torch.device(config.device)
    model = build_model(config).to(device)
    param_count = count_parameters(model)
    log.info("ml_model_built", model_key=config.model_key, params=param_count)

    weights = torch.tensor(meta["class_weights"], dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=2
    )

    # 3) 학습 루프
    best_val_loss = float("inf")
    best_state: dict[str, Any] | None = None
    best_val_acc = 0.0
    best_val_f1 = 0.0
    patience_counter = 0
    history: list[dict[str, float]] = []
    confusion = [[0] * config.num_classes for _ in range(config.num_classes)]

    for epoch in range(1, config.epochs + 1):
        model.train()
        train_losses = []
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))

        train_loss = float(np.mean(train_losses)) if train_losses else 0.0

        # validation
        if len(val_arr) > 0:
            val_loss, val_acc, val_f1, cm = _evaluate(
                model, val_loader, criterion, device, config.num_classes
            )
        else:
            val_loss, val_acc, val_f1, cm = train_loss, 0.0, 0.0, [[0] * config.num_classes for _ in range(config.num_classes)]

        scheduler.step(val_loss)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "val_f1": val_f1,
                "lr": float(optimizer.param_groups[0]["lr"]),
            }
        )
        log.info(
            "ml_epoch",
            epoch=epoch,
            train_loss=round(train_loss, 4),
            val_loss=round(val_loss, 4),
            val_acc=round(val_acc, 4),
            val_f1=round(val_f1, 4),
        )

        # 진행률: 15% + (학습 진척에 따라 70%)
        _notify(progress_cb, 15 + int(70 * epoch / max(1, config.epochs)))

        # EarlyStopping
        if val_loss < best_val_loss - 1e-5:
            best_val_loss = val_loss
            best_val_acc = val_acc
            best_val_f1 = val_f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            confusion = cm
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                log.info("ml_early_stopped", epoch=epoch, best_val_loss=best_val_loss)
                break

    # 4) 저장
    if best_state is None:
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    save_dir = config.model_path()
    os.makedirs(save_dir, exist_ok=True)

    torch.save(best_state, os.path.join(save_dir, "model.pt"))
    _save_scaler(scaler, os.path.join(save_dir, "scaler.joblib"))

    duration = time.time() - started

    meta_full = {
        "stock_code": config.stock_code,
        "horizon_days": config.horizon_days,
        "lookback_days": config.lookback_days,
        "features": list(config.features),
        "up_threshold": config.up_threshold,
        "down_threshold": config.down_threshold,
        "hidden_size": config.hidden_size,
        "num_layers": config.num_layers,
        "dropout": config.dropout,
        "epochs_run": len(history),
        "best_val_loss": best_val_loss,
        "best_val_acc": best_val_acc,
        "best_val_f1": best_val_f1,
        "label_dist": meta["label_dist"],
        "class_weights": meta["class_weights"],
        "model_param_count": param_count,
        "duration_sec": duration,
        "trained_at": datetime.now(UTC).isoformat(),
        "confusion_matrix": confusion,
        "history": history,
    }
    with open(os.path.join(save_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_full, f, ensure_ascii=False, indent=2)

    _notify(progress_cb, 100)
    log.info(
        "ml_train_done",
        model_key=config.model_key,
        save_dir=save_dir,
        duration_sec=round(duration, 2),
    )

    return TrainResult(
        model_key=config.model_key,
        model_dir=save_dir,
        epochs_run=len(history),
        best_val_loss=best_val_loss,
        best_val_acc=best_val_acc,
        best_val_f1=best_val_f1,
        train_history=history,
        confusion_matrix=confusion,
        label_dist=meta["label_dist"],
        class_weights=meta["class_weights"],
        duration_sec=duration,
        model_param_count=param_count,
        finished_at=meta_full["trained_at"],
    )


def _evaluate(
    model: Any,
    loader: Any,
    criterion: Any,
    device: Any,
    num_classes: int,
) -> tuple[float, float, float, list[list[int]]]:
    """val 평가."""
    torch, _nn, _optim = _import_torch()

    model.eval()
    losses = []
    all_preds: list[int] = []
    all_labels: list[int] = []
    with torch.no_grad():
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            logits = model(xb)
            loss = criterion(logits, yb)
            losses.append(float(loss.item()))
            preds = logits.argmax(dim=-1).detach().cpu().numpy().tolist()
            labels = yb.detach().cpu().numpy().tolist()
            all_preds.extend(preds)
            all_labels.extend(labels)

    mean_loss = float(np.mean(losses)) if losses else 0.0
    if not all_preds:
        empty_cm = [[0] * num_classes for _ in range(num_classes)]
        return mean_loss, 0.0, 0.0, empty_cm

    acc = float(np.mean(np.array(all_preds) == np.array(all_labels)))
    f1 = _macro_f1(all_labels, all_preds, num_classes)
    cm = _confusion_matrix(all_labels, all_preds, num_classes)
    return mean_loss, acc, f1, cm


def _macro_f1(labels: list[int], preds: list[int], num_classes: int) -> float:
    """sklearn 의존성 없이 macro F1 계산."""
    f1_scores = []
    for c in range(num_classes):
        tp = sum(1 for p, lab in zip(preds, labels, strict=False) if p == c and lab == c)
        fp = sum(1 for p, lab in zip(preds, labels, strict=False) if p == c and lab != c)
        fn = sum(1 for p, lab in zip(preds, labels, strict=False) if p != c and lab == c)
        if tp == 0:
            f1_scores.append(0.0)
            continue
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        if (precision + recall) == 0:
            f1_scores.append(0.0)
        else:
            f1_scores.append(2 * precision * recall / (precision + recall))
    return float(np.mean(f1_scores)) if f1_scores else 0.0


def _confusion_matrix(labels: list[int], preds: list[int], num_classes: int) -> list[list[int]]:
    cm = [[0] * num_classes for _ in range(num_classes)]
    for p, lab in zip(preds, labels, strict=False):
        if 0 <= lab < num_classes and 0 <= p < num_classes:
            cm[lab][p] += 1
    return cm


def _save_scaler(scaler: Any, path: str) -> None:
    import joblib

    joblib.dump(scaler, path)


def _notify(cb: Any, pct: int) -> None:
    if cb is not None:
        import contextlib

        with contextlib.suppress(Exception):  # 진행률 콜백 예외는 흐름과 무관
            cb(pct)


# ============================================================================
# 멀티 종목 학습 (섹터 / 글로벌)
# ============================================================================
@dataclass
class MultiStockTrainResult:
    """섹터/글로벌 학습 결과."""

    model_key: str           # 예: "sector_SEMI_3d", "global_3d"
    model_kind: str          # "SECTOR" / "GLOBAL"
    model_dir: str
    epochs_run: int
    best_val_loss: float
    best_val_acc: float
    best_val_f1: float
    per_stock_val_acc: dict[str, float]
    train_history: list[dict[str, float]]
    confusion_matrix: list[list[int]]
    label_dist: dict[int, int]
    class_weights: list[float]
    stock_to_id: dict[str, int]
    duration_sec: float
    model_param_count: int
    n_stocks: int
    finished_at: str


def train_sector_model(
    sector_code: str,
    ohlcv_by_code: dict[str, pd.DataFrame],
    config: MLConfig,
    *,
    progress_cb: Any = None,
    model_dir_base: str | None = None,
) -> MultiStockTrainResult:
    """섹터 단위 공통 LSTM 학습.

    Args:
        sector_code: 섹터 식별자 (예: "SEMI", "FIN", "BIO")
        ohlcv_by_code: 섹터 내 종목들의 OHLCV
        config: MLConfig (stock_code 는 무시되고 sector 식별자로 대체)
        progress_cb: 진행률 콜백
        model_dir_base: 모델 저장 베이스 (None 이면 config.model_dir)

    저장 디렉토리: {ML_MODEL_DIR}/sector_{sector_code}_{horizon}d/
    """
    return _train_multi(
        kind="SECTOR",
        identifier=sector_code,
        ohlcv_by_code=ohlcv_by_code,
        config=config,
        progress_cb=progress_cb,
        model_dir_base=model_dir_base,
    )


def train_multistock_model(
    ohlcv_by_code: dict[str, pd.DataFrame],
    config: MLConfig,
    *,
    progress_cb: Any = None,
    model_dir_base: str | None = None,
    identifier: str = "global",
) -> MultiStockTrainResult:
    """글로벌(전 종목 공통) LSTM 학습 (종목 임베딩 포함).

    저장 디렉토리: {ML_MODEL_DIR}/global_{horizon}d/
    """
    return _train_multi(
        kind="GLOBAL",
        identifier=identifier,
        ohlcv_by_code=ohlcv_by_code,
        config=config,
        progress_cb=progress_cb,
        model_dir_base=model_dir_base,
    )


def _multi_model_key(kind: str, identifier: str, horizon: int) -> str:
    """멀티 종목 모델 키 생성."""
    if kind == "SECTOR":
        return f"sector_{identifier}_{horizon}d"
    return f"global_{horizon}d"


def _train_multi(
    *,
    kind: str,
    identifier: str,
    ohlcv_by_code: dict[str, pd.DataFrame],
    config: MLConfig,
    progress_cb: Any = None,
    model_dir_base: str | None = None,
) -> MultiStockTrainResult:
    """섹터/글로벌 공용 학습 루프."""
    torch, nn, optim = _import_torch()
    started = time.time()

    # 1) 데이터 준비
    _notify(progress_cb, 5)
    train_arr, val_arr, scaler, stock_to_id, meta = build_multistock_dataset_from_ohlcvs(
        ohlcv_by_code, config, use_sample_weight=(kind == "GLOBAL")
    )
    n_stocks = len(stock_to_id)
    log.info(
        "ml_multi_dataset_built",
        kind=kind,
        identifier=identifier,
        n_stocks=n_stocks,
        n_train=len(train_arr),
        n_val=len(val_arr),
    )
    _notify(progress_cb, 15)

    train_loader, val_loader = make_multi_loaders(
        train_arr, val_arr, batch_size=config.batch_size,
        with_sample_weight=(kind == "GLOBAL"),
    )

    # 2) 모델
    device = torch.device(config.device)
    if kind == "SECTOR":
        model = build_sector_model(config).to(device)
        embed_dim = 0
    else:
        embed_dim = 8
        model = build_multistock_model(config, num_stocks=n_stocks, embed_dim=embed_dim).to(device)
    param_count = count_parameters(model)
    log.info("ml_multi_model_built", kind=kind, params=param_count, n_stocks=n_stocks)

    weights = torch.tensor(meta["class_weights"], dtype=torch.float32, device=device)
    # sample weight 적용을 위해 reduction='none' 사용
    criterion = nn.CrossEntropyLoss(weight=weights, reduction="none")
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=2
    )

    # 3) 학습 루프
    best_val_loss = float("inf")
    best_state: dict[str, Any] | None = None
    best_val_acc = 0.0
    best_val_f1 = 0.0
    best_per_stock_acc: dict[str, float] = {}
    patience_counter = 0
    history: list[dict[str, float]] = []
    confusion = [[0] * config.num_classes for _ in range(config.num_classes)]

    id_to_stock = {sid: code for code, sid in stock_to_id.items()}

    for epoch in range(1, config.epochs + 1):
        model.train()
        train_losses: list[float] = []
        for batch in train_loader:
            # batch: (X, y, stock_id, [weight])
            if len(batch) == 4:
                xb, yb, sidb, wb = batch
                wb = wb.to(device)
            else:
                xb, yb, sidb = batch
                wb = None
            xb = xb.to(device)
            yb = yb.to(device)
            sidb = sidb.to(device)

            optimizer.zero_grad()
            if kind == "GLOBAL":
                logits = model(xb, sidb)
            else:
                logits = model(xb)
            losses = criterion(logits, yb)  # (batch,)
            if wb is not None:
                loss = (losses * wb).mean()
            else:
                loss = losses.mean()
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))

        train_loss = float(np.mean(train_losses)) if train_losses else 0.0

        # validation
        if len(val_arr) > 0:
            val_loss, val_acc, val_f1, cm, per_stock = _evaluate_multi(
                model, val_loader, criterion, device, config.num_classes,
                kind=kind, id_to_stock=id_to_stock,
            )
        else:
            val_loss = train_loss
            val_acc = 0.0
            val_f1 = 0.0
            cm = [[0] * config.num_classes for _ in range(config.num_classes)]
            per_stock = {}

        scheduler.step(val_loss)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "val_f1": val_f1,
                "lr": float(optimizer.param_groups[0]["lr"]),
            }
        )
        log.info(
            "ml_multi_epoch",
            kind=kind,
            epoch=epoch,
            train_loss=round(train_loss, 4),
            val_loss=round(val_loss, 4),
            val_acc=round(val_acc, 4),
        )

        _notify(progress_cb, 15 + int(70 * epoch / max(1, config.epochs)))

        if val_loss < best_val_loss - 1e-5:
            best_val_loss = val_loss
            best_val_acc = val_acc
            best_val_f1 = val_f1
            best_per_stock_acc = per_stock
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            confusion = cm
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                log.info("ml_multi_early_stopped", kind=kind, epoch=epoch)
                break

    # 4) 저장
    if best_state is None:
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model_key = _multi_model_key(kind, identifier, config.horizon_days)
    base = model_dir_base or config.model_dir
    save_dir = os.path.join(base, model_key)
    os.makedirs(save_dir, exist_ok=True)

    torch.save(best_state, os.path.join(save_dir, "model.pt"))
    _save_scaler(scaler, os.path.join(save_dir, "scaler.joblib"))

    duration = time.time() - started

    meta_full = {
        "model_kind": kind,                # "SECTOR" | "GLOBAL"
        "identifier": identifier,           # 섹터 코드 또는 "global"
        "horizon_days": config.horizon_days,
        "lookback_days": config.lookback_days,
        "features": list(config.features),
        "up_threshold": config.up_threshold,
        "down_threshold": config.down_threshold,
        "hidden_size": config.hidden_size,
        "num_layers": config.num_layers,
        "dropout": config.dropout,
        "embed_dim": (8 if kind == "GLOBAL" else 0),
        "num_stocks": n_stocks,
        "stock_to_id": stock_to_id,
        "epochs_run": len(history),
        "best_val_loss": best_val_loss,
        "best_val_acc": best_val_acc,
        "best_val_f1": best_val_f1,
        "per_stock_val_acc": best_per_stock_acc,
        "label_dist": meta["label_dist"],
        "class_weights": meta["class_weights"],
        "per_stock_counts": meta["per_stock_counts"],
        "model_param_count": param_count,
        "duration_sec": duration,
        "trained_at": datetime.now(UTC).isoformat(),
        "confusion_matrix": confusion,
        "history": history,
    }
    with open(os.path.join(save_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_full, f, ensure_ascii=False, indent=2)

    _notify(progress_cb, 100)
    log.info(
        "ml_multi_train_done",
        kind=kind,
        identifier=identifier,
        model_key=model_key,
        save_dir=save_dir,
        duration_sec=round(duration, 2),
        n_stocks=n_stocks,
    )

    return MultiStockTrainResult(
        model_key=model_key,
        model_kind=kind,
        model_dir=save_dir,
        epochs_run=len(history),
        best_val_loss=best_val_loss,
        best_val_acc=best_val_acc,
        best_val_f1=best_val_f1,
        per_stock_val_acc=best_per_stock_acc,
        train_history=history,
        confusion_matrix=confusion,
        label_dist=meta["label_dist"],
        class_weights=meta["class_weights"],
        stock_to_id=stock_to_id,
        duration_sec=duration,
        model_param_count=param_count,
        n_stocks=n_stocks,
        finished_at=meta_full["trained_at"],
    )


def _evaluate_multi(
    model: Any,
    loader: Any,
    criterion: Any,
    device: Any,
    num_classes: int,
    *,
    kind: str,
    id_to_stock: dict[int, str],
) -> tuple[float, float, float, list[list[int]], dict[str, float]]:
    """멀티 종목 평가. 글로벌 정확도 + 종목별 정확도 + macro F1.

    criterion 은 reduction='none' 라고 가정 → 평균 처리.
    """
    torch, _nn, _optim = _import_torch()

    model.eval()
    losses: list[float] = []
    all_preds: list[int] = []
    all_labels: list[int] = []
    all_sids: list[int] = []
    with torch.no_grad():
        for batch in loader:
            if len(batch) == 4:
                xb, yb, sidb, _wb = batch
            else:
                xb, yb, sidb = batch
            xb = xb.to(device)
            yb = yb.to(device)
            sidb = sidb.to(device)
            if kind == "GLOBAL":
                logits = model(xb, sidb)
            else:
                logits = model(xb)
            loss = criterion(logits, yb).mean()
            losses.append(float(loss.item()))
            preds = logits.argmax(dim=-1).detach().cpu().numpy().tolist()
            labels = yb.detach().cpu().numpy().tolist()
            sids = sidb.detach().cpu().numpy().tolist()
            all_preds.extend(preds)
            all_labels.extend(labels)
            all_sids.extend(sids)

    mean_loss = float(np.mean(losses)) if losses else 0.0
    if not all_preds:
        empty_cm = [[0] * num_classes for _ in range(num_classes)]
        return mean_loss, 0.0, 0.0, empty_cm, {}

    acc = float(np.mean(np.array(all_preds) == np.array(all_labels)))
    f1 = _macro_f1(all_labels, all_preds, num_classes)
    cm = _confusion_matrix(all_labels, all_preds, num_classes)

    # 종목별 정확도
    per_stock_acc: dict[str, float] = {}
    arr_p = np.array(all_preds)
    arr_l = np.array(all_labels)
    arr_s = np.array(all_sids)
    unique_sids = np.unique(arr_s)
    for sid in unique_sids:
        mask = arr_s == sid
        if mask.sum() == 0:
            continue
        acc_s = float((arr_p[mask] == arr_l[mask]).mean())
        code = id_to_stock.get(int(sid), str(sid))
        per_stock_acc[code] = acc_s

    return mean_loss, acc, f1, cm, per_stock_acc
