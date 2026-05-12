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
    make_loaders,
)
from app.services.ml_engine.model import build_model, count_parameters

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
