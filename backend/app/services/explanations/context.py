"""Build grounded explanation context from reconstructed match state."""

from __future__ import annotations

from app.core.exceptions import ExplanationError, InferenceError
from app.schemas.enums import KnowledgeHorizon
from app.schemas.explanation import (
    DeliverySnippet,
    ExplanationContext,
    MomentEvidence,
    WinProbabilityEvidence,
)
from app.schemas.state import DeliveryApplied, MatchState
from app.services.api.catalog import LoadedMatch
from app.services.intelligence import (
    detect_significant_moments,
    win_probabilities_for_match,
)
from app.services.ml.inference import predict_one
from app.services.ml.model_registry import ModelArtifact

RECENT_WINDOW = 6


def build_explanation_context(
    loaded: LoadedMatch,
    state: MatchState,
    artifact: ModelArtifact | None,
) -> ExplanationContext:
    unknown: list[str] = []
    notes: list[str] = []

    last_delivery = _snippet(state.last_delivery)
    recent = _recent_deliveries(loaded.states, state)
    win_probability, wp_note = _win_probability_evidence(loaded, state, artifact)
    if wp_note:
        notes.append(wp_note)
    moments = _moments_up_to(loaded, state, artifact)

    optional_fields = {
        "batting_team": state.batting_team,
        "bowling_team": state.bowling_team,
        "innings_number": state.innings_number,
        "target": state.target,
        "runs_remaining": state.runs_remaining,
        "wickets_remaining": state.wickets_remaining,
        "balls_remaining": state.balls_remaining,
        "required_run_rate": state.required_run_rate,
        "current_run_rate": state.current_run_rate,
        "last_delivery": last_delivery,
        "win_probability": win_probability,
    }
    unknown.extend(name for name, value in optional_fields.items() if value is None)

    if not loaded.match.info.teams:
        raise ExplanationError(
            "match context is missing teams",
            code="incomplete_context",
            status_code=400,
        )

    return ExplanationContext(
        source_match_id=state.source_match_id,
        teams=loaded.match.info.teams,
        batting_team=state.batting_team,
        bowling_team=state.bowling_team,
        innings_number=state.innings_number,
        innings_phase=state.innings_phase.value if state.innings_phase else None,
        score=state.innings_runs_at_delivery,
        wickets=state.innings_wickets,
        overs=state.overs,
        legal_balls=state.legal_balls,
        target=state.target,
        runs_remaining=state.runs_remaining,
        wickets_remaining=state.wickets_remaining,
        balls_remaining=state.balls_remaining,
        required_run_rate=state.required_run_rate,
        current_run_rate=state.current_run_rate,
        sequence=state.sequence,
        last_delivery=last_delivery,
        recent_deliveries=recent,
        significant_moments=moments,
        win_probability=win_probability,
        is_active_prediction_state=state.is_active_prediction_state,
        innings_complete=state.innings_complete,
        match_complete=state.match_complete,
        unknown_fields=tuple(unknown),
        notes=tuple(notes),
    )


def validate_context(context: ExplanationContext) -> None:
    if not context.source_match_id.strip():
        raise ExplanationError(
            "match context is missing a source match id",
            code="incomplete_context",
            status_code=400,
        )
    if not context.teams:
        raise ExplanationError(
            "match context is missing teams",
            code="incomplete_context",
            status_code=400,
        )


def _snippet(delivery: DeliveryApplied | None) -> DeliverySnippet | None:
    if delivery is None:
        return None
    return DeliverySnippet(
        sequence=delivery.sequence,
        actual_delivery=delivery.actual_delivery,
        batter=delivery.batter,
        bowler=delivery.bowler,
        non_striker=delivery.non_striker,
        total_runs=delivery.total_runs,
        batter_runs=delivery.batter_runs,
        extras_runs=delivery.extras_runs,
        is_legal_delivery=delivery.is_legal_delivery,
        is_wide=delivery.is_wide,
        is_noball=delivery.is_noball,
        wicket_kinds=tuple(wicket.kind for wicket in delivery.wickets),
    )


def _recent_deliveries(
    states: tuple[MatchState, ...],
    current: MatchState,
) -> tuple[DeliverySnippet, ...]:
    snippets: list[DeliverySnippet] = []
    for state in states:
        if state.sequence > current.sequence:
            break
        if state.knowledge_horizon != KnowledgeHorizon.AT_DELIVERY:
            continue
        if (
            current.innings_number is not None
            and state.innings_number != current.innings_number
        ):
            continue
        snippet = _snippet(state.last_delivery)
        if snippet is None:
            continue
        snippets.append(snippet)
    return tuple(snippets[-RECENT_WINDOW:])


def _win_probability_evidence(
    loaded: LoadedMatch,
    state: MatchState,
    artifact: ModelArtifact | None,
) -> tuple[WinProbabilityEvidence | None, str | None]:
    if artifact is None:
        return None, "win probability unavailable: model artifact is not loaded"
    try:
        prediction = predict_one(
            artifact,
            state,
            loaded.states,
            match=loaded.match,
        )
    except InferenceError as exc:
        return None, f"win probability unavailable: {exc}"
    metadata = artifact.metadata
    return (
        WinProbabilityEvidence(
            probability=prediction.probability,
            model_id=prediction.model_id,
            model_kind=metadata.model_kind,
            feature_schema_version=prediction.feature_schema_version,
            evaluation_is_meaningful=metadata.evaluation_is_meaningful,
            evaluation_limitation=metadata.evaluation_limitation,
        ),
        None,
    )


def _moments_up_to(
    loaded: LoadedMatch,
    state: MatchState,
    artifact: ModelArtifact | None,
) -> tuple[MomentEvidence, ...]:
    if artifact is None:
        return ()
    predictions = win_probabilities_for_match(
        loaded.match, artifact, states=loaded.states
    )
    detected = detect_significant_moments(loaded.states, predictions)
    return tuple(
        MomentEvidence(
            moment_type=item.moment_type.value,
            sequence=item.sequence,
            probability_before=item.probability_before,
            probability_after=item.probability_after,
            probability_change=item.probability_change,
            reasons=item.reasons,
        )
        for item in detected
        if item.sequence <= state.sequence
    )
