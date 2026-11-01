"""Fit baseline chase-win models on a match-level chronological split."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.core.exceptions import DatasetError
from app.services.ml.dataset_builder import TrainingDataset
from app.services.ml.evaluate import EvaluationReport, evaluate_binary_probabilities
from app.services.ml.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from app.services.ml.model_registry import ModelArtifact, ModelMetadata

RANDOM_SEED = 42
LOGISTIC_MAX_ITER = 1000
RANDOM_FOREST_TREES = 100
RANDOM_FOREST_MAX_DEPTH = 6
RANDOM_FOREST_MIN_LEAF = 20


class TrainedModel:
    def __init__(self, artifact: ModelArtifact, report: dict[str, EvaluationReport]):
        self.artifact = artifact
        self.report = report


def fit_baseline_models(dataset: TrainingDataset) -> dict[str, TrainedModel]:
    """Fit logistic regression and random forest on the train split only.

    Validation and test matches are never used during fitting. Validation
    metrics are diagnostic only; they do not select a model. The current
    official sample is too small for model selection or XGBoost.
    """

    train = dataset.examples_for("train")
    if not train:
        raise DatasetError("training split is empty")
    _assert_fit_uses_train_only(dataset, train)

    x_train = _feature_matrix(train)
    y_train = np.asarray([example.label for example in train], dtype=int)
    trained_at = datetime.now(UTC).isoformat()
    models: dict[str, TrainedModel] = {}

    logistic = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=LOGISTIC_MAX_ITER,
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    logistic.fit(x_train, y_train)
    models["logistic_regression"] = _wrap(
        estimator=logistic,
        kind="logistic_regression",
        dataset=dataset,
        trained_at=trained_at,
        hyperparameters={
            "max_iter": LOGISTIC_MAX_ITER,
            "class_weight": "balanced",
            "solver": "lbfgs",
            "random_state": RANDOM_SEED,
        },
    )

    forest = RandomForestClassifier(
        n_estimators=RANDOM_FOREST_TREES,
        max_depth=RANDOM_FOREST_MAX_DEPTH,
        min_samples_leaf=RANDOM_FOREST_MIN_LEAF,
        class_weight="balanced",
        random_state=RANDOM_SEED,
        n_jobs=1,
    )
    forest.fit(x_train, y_train)
    models["random_forest"] = _wrap(
        estimator=forest,
        kind="random_forest",
        dataset=dataset,
        trained_at=trained_at,
        hyperparameters={
            "n_estimators": RANDOM_FOREST_TREES,
            "max_depth": RANDOM_FOREST_MAX_DEPTH,
            "min_samples_leaf": RANDOM_FOREST_MIN_LEAF,
            "class_weight": "balanced",
            "random_state": RANDOM_SEED,
        },
    )

    models["heuristic"] = _wrap(
        estimator=None,
        kind="heuristic",
        dataset=dataset,
        trained_at=trained_at,
        hyperparameters={
            "rate_gap_weight": 0.12,
            "wicket_weight": 0.12,
            "resource_weight": 1.2,
            "intercept": -0.3,
        },
    )
    return models


def _wrap(
    *,
    estimator,
    kind: str,
    dataset: TrainingDataset,
    trained_at: str,
    hyperparameters: dict,
) -> TrainedModel:
    metadata = ModelMetadata(
        model_id=f"chase_wp_{kind}_{FEATURE_SCHEMA_VERSION}",
        model_kind=kind,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        feature_names=FEATURE_NAMES,
        trained_at=trained_at,
        train_match_ids=dataset.train_match_ids,
        validation_match_ids=dataset.validation_match_ids,
        test_match_ids=dataset.test_match_ids,
        n_train_rows=len(dataset.examples_for("train")),
        n_validation_rows=len(dataset.examples_for("validation")),
        n_test_rows=len(dataset.examples_for("test")),
        hyperparameters=hyperparameters,
        evaluation_is_meaningful=dataset.evaluation_is_meaningful,
        evaluation_limitation=dataset.evaluation_limitation,
        target_definition="1 if the regulation chasing team won; 0 if it lost",
        fitted_split="train",
        validation_role="diagnostic_only",
        notes=(
            (
                "Fitted only on chronological train matches. "
                "Validation is diagnostic only and is not used for model selection. "
                "Test data is never used during fitting. "
                "Terminal and inactive states are excluded."
            ),
        ),
    )
    artifact = ModelArtifact(estimator=estimator, metadata=metadata)
    reports = {
        split: _evaluate_split(artifact, dataset, split)
        for split in ("train", "validation", "test")
        if dataset.examples_for(split)
    }
    return TrainedModel(artifact=artifact, report=reports)


def _evaluate_split(
    artifact: ModelArtifact,
    dataset: TrainingDataset,
    split: str,
) -> EvaluationReport:
    examples = dataset.examples_for(split)
    proba = [float(artifact.predict_proba(example.features)) for example in examples]
    return evaluate_binary_probabilities(
        [example.label for example in examples],
        proba,
        match_ids=[example.source_match_id for example in examples],
        evaluation_is_meaningful=dataset.evaluation_is_meaningful and split == "test",
    )


def _assert_fit_uses_train_only(dataset: TrainingDataset, train) -> None:
    train_ids = {example.source_match_id for example in train}
    allowed = set(dataset.train_match_ids)
    forbidden = set(dataset.validation_match_ids) | set(dataset.test_match_ids)
    if train_ids - allowed:
        raise DatasetError("training rows are not isolated to train match ids")
    if train_ids & forbidden:
        raise DatasetError("validation or test matches leaked into model fitting")


def _feature_matrix(examples) -> np.ndarray:
    return np.asarray(
        [example.features.to_array(FEATURE_NAMES) for example in examples],
        dtype=float,
    )
