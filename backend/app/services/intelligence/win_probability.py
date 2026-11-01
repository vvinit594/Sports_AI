"""Match-level chase win-probability series from reconstructed states."""

from __future__ import annotations

from collections.abc import Sequence

from app.core.constants import DEFAULT_BALLS_PER_OVER
from app.schemas.match import NormalizedMatch
from app.schemas.state import MatchState
from app.services.match_engine import MatchStateEngine
from app.services.ml.features import is_chase_training_state
from app.services.ml.inference import ProbabilityPrediction, predict_one
from app.services.ml.model_registry import ModelArtifact


def eligible_chase_states(states: Sequence[MatchState]) -> list[MatchState]:
    return [state for state in states if is_chase_training_state(state)]


def win_probabilities_for_match(
    match: NormalizedMatch,
    artifact: ModelArtifact,
    *,
    states: Sequence[MatchState] | None = None,
) -> list[ProbabilityPrediction]:
    reconstructed = list(states) if states is not None else MatchStateEngine(match).reconstruct()
    predictions: list[ProbabilityPrediction] = []
    for state in eligible_chase_states(reconstructed):
        predictions.append(
            predict_one(
                artifact,
                state,
                reconstructed,
                match=match,
                balls_per_over=match.info.balls_per_over or DEFAULT_BALLS_PER_OVER,
            )
        )
    return predictions
