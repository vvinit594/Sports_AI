"""Win-probability inference from a persisted or in-memory model."""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.constants import DEFAULT_BALLS_PER_OVER
from app.core.exceptions import FeatureError, InferenceError
from app.schemas.match import NormalizedMatch
from app.schemas.state import MatchState
from app.services.ml.features import (
    FEATURE_SCHEMA_VERSION,
    extract_feature_vector,
    is_chase_training_state,
)
from app.services.ml.model_registry import ModelArtifact


class ProbabilityPrediction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_match_id: str
    sequence: int
    probability: float
    model_id: str
    feature_schema_version: str = FEATURE_SCHEMA_VERSION

    @field_validator("probability")
    @classmethod
    def _bounded(cls, value: float) -> float:
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            raise ValueError("probability must be a finite value in [0, 1]")
        return float(value)


class InferenceResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prediction: ProbabilityPrediction | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.prediction is not None and self.error is None


def predict_one(
    artifact: ModelArtifact,
    state: MatchState,
    history: Sequence[MatchState] = (),
    *,
    match: NormalizedMatch | None = None,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
) -> ProbabilityPrediction:
    """Predict P(chasing team wins) for one active chase state."""

    _refuse_invalid_state(state)
    try:
        features = extract_feature_vector(
            state,
            history,
            match=match,
            balls_per_over=balls_per_over,
            require_active=True,
        )
    except FeatureError as exc:
        raise InferenceError(str(exc)) from exc
    if not features.is_complete(artifact.metadata.feature_names):
        raise InferenceError("incomplete or non-finite feature vector")
    raw = artifact.predict_proba(features)
    probability = _validated_probability(raw)
    return ProbabilityPrediction(
        source_match_id=state.source_match_id,
        sequence=state.sequence,
        probability=probability,
        model_id=artifact.metadata.model_id,
        feature_schema_version=artifact.metadata.feature_schema_version,
    )


def predict_batch(
    artifact: ModelArtifact,
    states: Sequence[MatchState],
    *,
    match: NormalizedMatch | None = None,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
) -> list[InferenceResult]:
    results: list[InferenceResult] = []
    for state in states:
        try:
            prediction = predict_one(
                artifact,
                state,
                states,
                match=match,
                balls_per_over=balls_per_over,
            )
            results.append(InferenceResult(prediction=prediction))
        except InferenceError as exc:
            results.append(InferenceResult(error=str(exc)))
    return results


def _refuse_invalid_state(state: MatchState) -> None:
    if state.innings_complete or state.match_complete:
        raise InferenceError("refusing inference on a completed innings or match")
    if not state.is_active_prediction_state or state.source_delivery_after_terminal:
        raise InferenceError("refusing inference on a terminal or inactive state")
    if not is_chase_training_state(state):
        raise InferenceError(
            "chase-win model inference requires an active regulation chase state"
        )


def _validated_probability(value: float) -> float:
    if not math.isfinite(value):
        raise InferenceError("model returned a non-finite probability")
    if value < 0.0 or value > 1.0:
        raise InferenceError(f"model returned probability outside [0, 1]: {value}")
    return float(value)
