"""Deterministic significant-moment detector from win-probability swings.

This is not a second classifier. Moments are emitted from configured
thresholds on probability change, wickets, boundaries, and chase-equation
shifts, with cooldown and duplicate suppression.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

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
    """Detect moments from consecutive eligible chase predictions.

    ``predictions`` must be ordered by sequence and refer to the same match
    as ``states``. Duplicate sequences are ignored. After a moment is emitted,
    further moments are suppressed until ``cooldown_deliveries`` later
    sequences have passed.
    """

    settings = config or MomentDetectorConfig()
    by_sequence = {prediction.sequence: prediction for prediction in predictions}
    ordered = [state for state in states if state.sequence in by_sequence]
    ordered.sort(key=lambda state: state.sequence)

    moments: list[SignificantMoment] = []
    last_emitted_sequence: int | None = None
    seen_sequences: set[int] = set()

    for previous, current in zip(ordered, ordered[1:]):
        if current.sequence in seen_sequences:
            continue
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

        seen_sequences.add(current.sequence)
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
        delivery
        and any(wicket.counts_as_wicket for wicket in delivery.wickets)
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


def _context(state: MatchState, *, extra_types: Sequence[MomentType]) -> dict[str, object]:
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
