"""Evaluation metrics for chase-win probability models."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

class EvaluationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    n_rows: int
    n_matches: int
    n_positive: int
    n_negative: int
    log_loss: float | None = None
    brier_score: float | None = None
    roc_auc: float | None = None
    accuracy: float | None = None
    expected_calibration_error: float | None = None
    both_classes_present: bool
    evaluation_is_meaningful: bool
    notes: tuple[str, ...] = ()


def evaluate_binary_probabilities(
    y_true: Sequence[int],
    y_proba: Sequence[float],
    *,
    match_ids: Sequence[str] | None = None,
    evaluation_is_meaningful: bool = False,
    n_bins: int = 10,
) -> EvaluationReport:
    labels = np.asarray(list(y_true), dtype=int)
    proba = np.asarray(list(y_proba), dtype=float)
    if labels.shape != proba.shape:
        raise ValueError("y_true and y_proba must have the same length")
    if labels.size == 0:
        return EvaluationReport(
            n_rows=0,
            n_matches=0 if match_ids is None else len(set(match_ids)),
            n_positive=0,
            n_negative=0,
            both_classes_present=False,
            evaluation_is_meaningful=False,
            notes=("empty evaluation set",),
        )

    if np.any(~np.isfinite(proba)) or np.any(proba < 0.0) or np.any(proba > 1.0):
        raise ValueError("probabilities must be finite values in [0, 1]")

    n_positive = int(np.sum(labels == 1))
    n_negative = int(np.sum(labels == 0))
    both = n_positive > 0 and n_negative > 0
    notes: list[str] = []
    if not both:
        notes.append("ROC-AUC omitted because the evaluation set has one class")
    if not evaluation_is_meaningful:
        notes.append(
            "Metrics are from a held-out split but the corpus is too small "
            "for a meaningful generalization claim"
        )

    clipped = np.clip(proba, 1e-15, 1 - 1e-15)
    return EvaluationReport(
        n_rows=int(labels.size),
        n_matches=0 if match_ids is None else len(set(match_ids)),
        n_positive=n_positive,
        n_negative=n_negative,
        log_loss=float(log_loss(labels, clipped, labels=[0, 1])),
        brier_score=float(brier_score_loss(labels, proba)),
        roc_auc=float(roc_auc_score(labels, proba)) if both else None,
        accuracy=float(accuracy_score(labels, (proba >= 0.5).astype(int))),
        expected_calibration_error=_expected_calibration_error(labels, proba, n_bins),
        both_classes_present=both,
        evaluation_is_meaningful=evaluation_is_meaningful,
        notes=tuple(notes),
    )


def write_calibration_plot(
    y_true: Sequence[int],
    y_proba: Sequence[float],
    output_path: str | Path,
    *,
    n_bins: int = 10,
    title: str = "Calibration",
) -> Path | None:
    labels = np.asarray(list(y_true), dtype=int)
    proba = np.asarray(list(y_proba), dtype=float)
    if labels.size == 0:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.calibration import calibration_curve
    except ImportError:
        return None

    fraction_of_positives, mean_predicted = calibration_curve(
        labels, proba, n_bins=n_bins, strategy="uniform"
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(5, 5))
    axis.plot([0, 1], [0, 1], linestyle="--", color="gray", label="perfect")
    axis.plot(mean_predicted, fraction_of_positives, marker="o", label="model")
    axis.set_xlabel("Predicted chase-win probability")
    axis.set_ylabel("Observed chase-win frequency")
    axis.set_title(title)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)
    return path


def _expected_calibration_error(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    n_bins: int,
) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for index in range(n_bins):
        if index == n_bins - 1:
            mask = (y_proba >= bins[index]) & (y_proba <= bins[index + 1])
        else:
            mask = (y_proba >= bins[index]) & (y_proba < bins[index + 1])
        if not np.any(mask):
            continue
        acc = float(np.mean(y_true[mask]))
        conf = float(np.mean(y_proba[mask]))
        ece += (float(np.mean(mask))) * abs(acc - conf)
    return float(ece)
