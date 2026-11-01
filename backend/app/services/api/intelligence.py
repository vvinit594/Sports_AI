"""API wrappers around Phase 2 win-probability and moment detection."""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.exceptions import IntelligenceError, ModelRegistryError
from app.schemas.api import (
    ModelMetadataView,
    MomentsResponse,
    MomentView,
    ProbabilityPredictionView,
    WinProbabilityResponse,
)
from app.services.api.catalog import LoadedMatch, MatchCatalog
from app.services.intelligence import (
    detect_significant_moments,
    win_probabilities_for_match,
)
from app.services.ml.inference import ProbabilityPrediction
from app.services.ml.model_registry import ModelArtifact, ModelMetadata, load_model

logger = logging.getLogger(__name__)

MODEL_UNAVAILABLE = "model_artifact_missing"
UNSUPPORTED_STATE = "unsupported_state"


def load_optional_model(settings: Settings) -> ModelArtifact | None:
    """Load a registry artifact if one exists. Never invent a substitute model."""

    explicit = settings.resolved_model_path()
    if explicit is not None:
        try:
            artifact = load_model(explicit)
        except ModelRegistryError as exc:
            logger.warning("configured model path could not be loaded: %s", exc)
            return None
        logger.info("loaded model artifact %s", artifact.metadata.model_id)
        return artifact

    model_dir = settings.resolved_model_dir()
    if not model_dir.exists():
        logger.info("model directory does not exist: %s", model_dir)
        return None
    candidates = sorted(
        model_dir.glob("*.joblib"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            artifact = load_model(path)
        except ModelRegistryError as exc:
            logger.warning("skipped unreadable model artifact %s: %s", path.name, exc)
            continue
        logger.info(
            "loaded model artifact %s from %s", artifact.metadata.model_id, path.name
        )
        return artifact
    logger.info("no loadable model artifact in %s", model_dir)
    return None


class IntelligenceService:
    def __init__(self, catalog: MatchCatalog, artifact: ModelArtifact | None):
        self.catalog = catalog
        self.artifact = artifact

    def model_view(self) -> ModelMetadataView | None:
        if self.artifact is None:
            return None
        return to_model_view(self.artifact.metadata)

    def win_probability(
        self,
        match_id: str,
        *,
        sequence: int | None = None,
    ) -> WinProbabilityResponse:
        loaded = self.catalog.get(match_id)
        if sequence is not None:
            loaded.state_at(sequence)
        if self.artifact is None:
            return WinProbabilityResponse(
                source_match_id=match_id,
                available=False,
                unavailable_reason=MODEL_UNAVAILABLE,
                requested_sequence=sequence,
                predictions=[],
                model=None,
            )
        predictions = win_probabilities_for_match(
            loaded.match, self.artifact, states=loaded.states
        )
        if sequence is None:
            return WinProbabilityResponse(
                source_match_id=match_id,
                available=True,
                unavailable_reason=None,
                requested_sequence=None,
                predictions=[to_prediction_view(item) for item in predictions],
                model=self.model_view(),
            )
        selected = [item for item in predictions if item.sequence == sequence]
        if not selected:
            return WinProbabilityResponse(
                source_match_id=match_id,
                available=False,
                unavailable_reason=UNSUPPORTED_STATE,
                requested_sequence=sequence,
                predictions=[],
                model=self.model_view(),
            )
        return WinProbabilityResponse(
            source_match_id=match_id,
            available=True,
            unavailable_reason=None,
            requested_sequence=sequence,
            predictions=[to_prediction_view(item) for item in selected],
            model=self.model_view(),
        )

    def moments(self, match_id: str) -> MomentsResponse:
        loaded = self.catalog.get(match_id)
        if self.artifact is None:
            return MomentsResponse(
                source_match_id=match_id,
                available=False,
                unavailable_reason=MODEL_UNAVAILABLE,
                count=0,
                moments=[],
                model=None,
            )
        predictions = win_probabilities_for_match(
            loaded.match, self.artifact, states=loaded.states
        )
        try:
            detected = detect_significant_moments(loaded.states, predictions)
        except IntelligenceError as exc:
            logger.warning("moment detection refused for %s: %s", match_id, exc)
            return MomentsResponse(
                source_match_id=match_id,
                available=False,
                unavailable_reason="detection_refused",
                count=0,
                moments=[],
                model=self.model_view(),
            )
        return MomentsResponse(
            source_match_id=match_id,
            available=True,
            unavailable_reason=None,
            count=len(detected),
            moments=[to_moment_view(item) for item in detected],
            model=self.model_view(),
        )

    def predictions_for(self, loaded: LoadedMatch) -> list[ProbabilityPrediction]:
        if self.artifact is None:
            return []
        return win_probabilities_for_match(
            loaded.match, self.artifact, states=loaded.states
        )


def to_model_view(metadata: ModelMetadata) -> ModelMetadataView:
    return ModelMetadataView(
        model_id=metadata.model_id,
        model_kind=metadata.model_kind,
        feature_schema_version=metadata.feature_schema_version,
        evaluation_is_meaningful=metadata.evaluation_is_meaningful,
        evaluation_limitation=metadata.evaluation_limitation,
        trained_at=metadata.trained_at,
        n_train_rows=metadata.n_train_rows,
        fitted_split=metadata.fitted_split,
        validation_role=metadata.validation_role,
        notes=metadata.notes,
    )


def to_prediction_view(prediction: ProbabilityPrediction) -> ProbabilityPredictionView:
    return ProbabilityPredictionView(
        source_match_id=prediction.source_match_id,
        sequence=prediction.sequence,
        probability=prediction.probability,
        model_id=prediction.model_id,
        feature_schema_version=prediction.feature_schema_version,
    )


def to_moment_view(moment: object) -> MomentView:
    payload = moment.model_dump()  # type: ignore[attr-defined]
    return MomentView(
        moment_type=str(payload["moment_type"]),
        source_match_id=payload["source_match_id"],
        sequence=payload["sequence"],
        probability_before=payload["probability_before"],
        probability_after=payload["probability_after"],
        probability_change=payload["probability_change"],
        reasons=tuple(payload["reasons"]),
        match_context=dict(payload.get("match_context") or {}),
    )
