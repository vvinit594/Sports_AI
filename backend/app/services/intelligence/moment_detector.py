"""Deterministic significant-moment detector from win-probability swings.

This is not a second classifier. Moments are emitted from configured
thresholds on probability change, wickets, boundaries, and chase-equation
shifts, with cooldown and duplicate suppression.

Inputs are validated before detection:

- Every prediction and state must share one ``source_match_id``.
- Conflicting duplicate prediction sequences are rejected.
- Identical duplicate predictions are deduplicated.
- Predictions with no matching state are rejected.
- States without a prediction are ignored.
- Results are computed after sorting by delivery sequence, so caller order
  does not change the output.
- Cooldown is the difference in delivery ``sequence`` numbers after the last
  emitted moment, not a count of list items or detected events.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from itertools import pairwise

from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import IntelligenceError
from app.schemas.state import MatchState
from app.services.ml.inference import ProbabilityPrediction


class MomentType(StrEnum):
    WIN_PROBABILITY_SWING = "win_probability_swing"
    HIGH_PRESSURE_WICKET = "high_pressure_wicket"
    MAJOR_BOUNDARY = "major_boundary"
    CHASE_EQUATION_SHIFT = "chase_equation_shift"


class MomentDetectorConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    probability_swing_threshold: float = 0.08
    high_pressure_required_run_rate: float = 10.0
    high_pressure_balls_remaining: int = 36
    major_boundary_runs: int = 4
    chase_equation_rrr_delta: float = 1.5
    cooldown_deliveries: int = 6


class SignificantMoment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    moment_type: MomentType
    source_match_id: str
    sequence: int
    probability_before: float
    probability_after: float
    probability_change: float
    reasons: tuple[str, ...]
    match_context: dict[str, object] = Field(default_factory=dict)


def detect_significant_moments(
    states: Sequence[MatchState],
    predictions: Sequence[ProbabilityPrediction],
    *,
    config: MomentDetectorConfig | None = None,
) -> list[SignificantMoment]:
    """Detect moments from consecutive eligible chase predictions for one match."""

    settings = config or MomentDetectorConfig()
    if not predictions:
        return []

    match_id = _require_single_match_id(states, predictions)
    by_sequence = _index_predictions(predictions, match_id)
    ordered = _align_states(states, by_sequence, match_id)

    moments: list[SignificantMoment] = []
    last_emitted_sequence: int | None = None

    for previous, current in pairwise(ordered):
        if (
            last_emitted_sequence is not None
            and current.sequence - last_emitted_sequence < settings.cooldown_deliveries
        ):
            continue

        before = by_sequence[previous.sequence].probability
        after = by_sequence[current.sequence].probability
        change = abs(after - before)
        types, reasons = _classify(previous, current, change, settings)
        if not types:
            continue

        last_emitted_sequence = current.sequence
        primary = types[0]
        moments.append(
            SignificantMoment(
                moment_type=primary,
                source_match_id=current.source_match_id,
                sequence=current.sequence,
                probability_before=before,
                probability_after=after,
                probability_change=change,
                reasons=tuple(reasons),
                match_context=_context(current, extra_types=types[1:]),
            )
        )
    return moments


def _require_single_match_id(
    states: Sequence[MatchState],
    predictions: Sequence[ProbabilityPrediction],
) -> str:
    prediction_ids = {item.source_match_id for item in predictions}
    if len(prediction_ids) != 1:
        raise IntelligenceError(
            "predictions must all belong to the same source_match_id"
        )
    match_id = next(iter(prediction_ids))
    state_ids = {state.source_match_id for state in states}
    if any(state_id != match_id for state_id in state_ids):
        raise IntelligenceError(
            f"states include match ids {sorted(state_ids)} which do not match {match_id}"
        )
    return match_id


def _index_predictions(
    predictions: Sequence[ProbabilityPrediction],
    match_id: str,
) -> dict[int, ProbabilityPrediction]:
    indexed: dict[int, ProbabilityPrediction] = {}
    for prediction in predictions:
        if prediction.source_match_id != match_id:
            raise IntelligenceError(
                "predictions must all belong to the same source_match_id"
            )
        existing = indexed.get(prediction.sequence)
        if existing is None:
            indexed[prediction.sequence] = prediction
            continue
        if existing.model_dump() != prediction.model_dump():
            raise IntelligenceError(
                f"conflicting predictions for {match_id} sequence {prediction.sequence}"
            )
    return indexed


def _align_states(
    states: Sequence[MatchState],
    predictions: dict[int, ProbabilityPrediction],
    match_id: str,
) -> list[MatchState]:
    unique: dict[int, MatchState] = {}
    for state in states:
        if state.source_match_id != match_id:
            raise IntelligenceError(
                f"state {state.source_match_id}#{state.sequence} is not from {match_id}"
            )
        existing = unique.get(state.sequence)
        if existing is None:
            unique[state.sequence] = state
            continue
        if existing.model_dump() != state.model_dump():
            raise IntelligenceError(
                f"conflicting states for {match_id} sequence {state.sequence}"
            )

    missing = sorted(sequence for sequence in predictions if sequence not in unique)
    if missing:
        raise IntelligenceError(
            f"predictions have no matching state in {match_id}: {missing}"
        )
    return [unique[sequence] for sequence in sorted(predictions)]


def _classify(
    previous: MatchState,
    current: MatchState,
    change: float,
    config: MomentDetectorConfig,
) -> tuple[list[MomentType], list[str]]:
    types: list[MomentType] = []
    reasons: list[str] = []
    delivery = current.last_delivery

    if change >= config.probability_swing_threshold:
        types.append(MomentType.WIN_PROBABILITY_SWING)
        reasons.append(
            f"win probability changed by {change:.3f} "
            f"(threshold {config.probability_swing_threshold:.3f})"
        )

    counting_wicket = bool(
        delivery and any(wicket.counts_as_wicket for wicket in delivery.wickets)
    )
    high_pressure = _is_high_pressure(current, config)
    if counting_wicket and high_pressure:
        types.append(MomentType.HIGH_PRESSURE_WICKET)
        rrr = current.required_run_rate
        balls = current.balls_remaining
        reasons.append(
            "wicket in a high-pressure chase "
            f"(RRR {rrr if rrr is not None else 'unknown'}, "
            f"{balls if balls is not None else 'unknown'} balls remaining)"
        )

    if delivery and delivery.batter_runs >= config.major_boundary_runs:
        types.append(MomentType.MAJOR_BOUNDARY)
        reasons.append(f"scoring event of {delivery.batter_runs} batter runs")

    rrr_delta = _rrr_delta(previous, current)
    if rrr_delta is not None and rrr_delta >= config.chase_equation_rrr_delta:
        types.append(MomentType.CHASE_EQUATION_SHIFT)
        reasons.append(
            f"required run rate changed by {rrr_delta:.2f} "
            f"(threshold {config.chase_equation_rrr_delta:.2f})"
        )

    return types, reasons


def _is_high_pressure(state: MatchState, config: MomentDetectorConfig) -> bool:
    rrr = state.required_run_rate
    balls = state.balls_remaining
    high_rrr = rrr is not None and rrr >= config.high_pressure_required_run_rate
    late = balls is not None and balls <= config.high_pressure_balls_remaining
    return high_rrr or late


def _rrr_delta(previous: MatchState, current: MatchState) -> float | None:
    if previous.required_run_rate is None or current.required_run_rate is None:
        return None
    return abs(current.required_run_rate - previous.required_run_rate)


def _context(
    state: MatchState, *, extra_types: Sequence[MomentType]
) -> dict[str, object]:
    return {
        "innings_number": state.innings_number,
        "batting_team": state.batting_team,
        "bowling_team": state.bowling_team,
        "score": state.innings_runs_at_delivery,
        "wickets": state.innings_wickets,
        "overs": state.overs,
        "target": state.target,
        "runs_remaining": state.runs_remaining,
        "balls_remaining": state.balls_remaining,
        "required_run_rate": state.required_run_rate,
        "additional_moment_types": [item.value for item in extra_types],
    }
