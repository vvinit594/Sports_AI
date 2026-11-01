"""Serialize and load chase-win models with schema metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import ModelRegistryError
from app.services.ml.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, FeatureVector
from app.services.ml.heuristic import heuristic_chase_win_probability


class ModelMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str
    model_kind: str
    feature_schema_version: str
    feature_names: tuple[str, ...]
    trained_at: str
    train_match_ids: tuple[str, ...] = ()
    validation_match_ids: tuple[str, ...] = ()
    test_match_ids: tuple[str, ...] = ()
    n_train_rows: int = 0
    n_validation_rows: int = 0
    n_test_rows: int = 0
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    evaluation_is_meaningful: bool = False
    evaluation_limitation: str | None = None
    target_definition: str
    notes: tuple[str, ...] = ()


class ModelArtifact:
    def __init__(self, estimator: Any, metadata: ModelMetadata):
        self.estimator = estimator
        self.metadata = metadata

    def predict_proba(self, features: FeatureVector) -> float:
        if features.schema_version != self.metadata.feature_schema_version:
            raise ModelRegistryError(
                f"feature schema {features.schema_version} does not match "
                f"{self.metadata.feature_schema_version}"
            )
        if not features.is_complete(self.metadata.feature_names):
            raise ModelRegistryError("incomplete or non-finite feature vector")
        if self.metadata.model_kind == "heuristic":
            return heuristic_chase_win_probability(features)
        if self.estimator is None:
            raise ModelRegistryError(f"{self.metadata.model_id} has no estimator")
        row = [features.to_array(self.metadata.feature_names)]
        probabilities = self.estimator.predict_proba(row)[0]
        classes = _estimator_classes(self.estimator)
        if 1 not in classes:
            return 0.0
        return float(probabilities[classes.index(1)])


def save_model(artifact: ModelArtifact, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": artifact.metadata.model_dump(),
        "estimator": artifact.estimator,
    }
    joblib.dump(payload, destination)
    return destination


def load_model(path: str | Path) -> ModelArtifact:
    source = Path(path)
    if not source.exists():
        raise ModelRegistryError(f"model file not found: {source}")
    try:
        payload = joblib.load(source)
    except Exception as exc:  # noqa: BLE001 - joblib may raise many types
        raise ModelRegistryError(f"unable to load model {source}: {exc}") from exc
    if not isinstance(payload, dict) or "metadata" not in payload:
        raise ModelRegistryError(f"{source} is not a PulseIQ model artifact")
    metadata = ModelMetadata.model_validate(payload["metadata"])
    if metadata.feature_schema_version != FEATURE_SCHEMA_VERSION:
        raise ModelRegistryError(
            f"artifact schema {metadata.feature_schema_version} is not "
            f"{FEATURE_SCHEMA_VERSION}"
        )
    if tuple(metadata.feature_names) != FEATURE_NAMES:
        raise ModelRegistryError("artifact feature names do not match the current schema")
    return ModelArtifact(estimator=payload.get("estimator"), metadata=metadata)


def _estimator_classes(estimator: Any) -> list[Any]:
    classes = getattr(estimator, "classes_", None)
    if classes is None and hasattr(estimator, "named_steps"):
        classes = estimator.named_steps["clf"].classes_
    if classes is None:
        raise ModelRegistryError("estimator does not expose class labels")
    return list(classes)
