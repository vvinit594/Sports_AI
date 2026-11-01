"""Ball-by-ball feature extraction from Phase 1 match states.

Features use only information known at the current state's timestamp.
Recent-window stats are taken from earlier deliveries in the same innings.
Terminal, post-penalty, and after-innings snapshots are not active
prediction states and are excluded from training by the dataset builder.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DEFAULT_BALLS_PER_OVER, STANDARD_WICKETS_TO_ALL_OUT
from app.core.exceptions import FeatureError
from app.schemas.enums import KnowledgeHorizon
from app.schemas.match import NormalizedMatch
from app.schemas.state import DeliveryApplied, MatchState

FEATURE_SCHEMA_VERSION = "chase_wp_v1"

FEATURE_NAMES: tuple[str, ...] = (
    "innings_number",
    "is_chase",
    "is_first_innings",
    "current_score",
    "wickets_lost",
    "wickets_remaining",
    "legal_balls",
    "balls_remaining",
    "scheduled_balls",
    "overs_remaining",
    "target",
    "runs_remaining",
    "current_run_rate",
    "required_run_rate",
    "target_pressure",
    "resources_remaining",
    "runs_last_6",
    "runs_last_12",
    "wickets_last_6",
    "wickets_last_12",
    "boundaries_last_6",
    "boundaries_last_12",
    "missing_target",
    "missing_balls_remaining",
    "missing_scheduled_balls",
    "missing_current_run_rate",
    "missing_required_run_rate",
    "missing_wickets_remaining",
)

_WINDOW_SHORT = 6
_WINDOW_LONG = 12


class FeatureVector(BaseModel):
    """Numeric features for one reconstructed match state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = FEATURE_SCHEMA_VERSION
    source_match_id: str
    sequence: int
    values: dict[str, float]
    missing: dict[str, bool] = Field(default_factory=dict)

    def to_array(self, feature_names: Sequence[str] = FEATURE_NAMES) -> list[float]:
        try:
            return [float(self.values[name]) for name in feature_names]
        except KeyError as exc:
            raise FeatureError(f"feature vector missing {exc}") from exc

    def is_complete(self, feature_names: Sequence[str] = FEATURE_NAMES) -> bool:
        return all(name in self.values for name in feature_names) and all(
            _is_finite(self.values[name]) for name in feature_names
        )


def is_active_feature_state(state: MatchState) -> bool:
    """True when the state may be used for live feature extraction."""

    return (
        state.is_active_prediction_state
        and not state.innings_complete
        and not state.match_complete
        and not state.source_delivery_after_terminal
        and not state.includes_post_innings_penalty
        and state.knowledge_horizon != KnowledgeHorizon.AFTER_INNINGS
        and state.innings_number is not None
    )


def is_chase_state(state: MatchState) -> bool:
    return (
        state.innings_number == 2
        and not state.is_super_over
        and state.target is not None
    )


def is_chase_training_state(state: MatchState) -> bool:
    """Active regulation chase state that may receive a match-level label."""

    return is_active_feature_state(state) and is_chase_state(state)


def extract_feature_vector(
    state: MatchState,
    history: Sequence[MatchState] = (),
    *,
    match: NormalizedMatch | None = None,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
    require_active: bool = True,
) -> FeatureVector:
    """Build a feature vector from one state and earlier same-innings states.

    ``history`` must contain only states with ``sequence < state.sequence``.
    Future deliveries are ignored even if a caller passes them.
    """

    if balls_per_over <= 0:
        raise FeatureError("balls_per_over must be positive")
    if require_active and not is_active_feature_state(state):
        raise FeatureError(
            f"state {state.source_match_id}#{state.sequence} is not an active "
            "prediction state"
        )
    if match is not None and match.source_match_id != state.source_match_id:
        raise FeatureError("history match id does not match the state")

    window = _window_delivery_states(state, history)
    recent_short = window[-_WINDOW_SHORT:]
    recent_long = window[-_WINDOW_LONG:]

    missing_target = state.target is None
    missing_balls = state.balls_remaining is None
    missing_scheduled = state.scheduled_balls is None
    missing_crr = state.current_run_rate is None
    missing_rrr = state.required_run_rate is None
    missing_wickets_remaining = state.wickets_remaining is None

    current_score = float(state.innings_runs_at_delivery)
    wickets_lost = float(state.innings_wickets)
    wickets_remaining = (
        float(state.wickets_remaining) if state.wickets_remaining is not None else 0.0
    )
    legal_balls = float(state.legal_balls)
    balls_remaining = (
        float(state.balls_remaining) if state.balls_remaining is not None else 0.0
    )
    scheduled_balls = (
        float(state.scheduled_balls) if state.scheduled_balls is not None else 0.0
    )
    overs_remaining = balls_remaining / float(balls_per_over)
    target = float(state.target) if state.target is not None else 0.0
    runs_remaining = (
        float(state.runs_remaining) if state.runs_remaining is not None else 0.0
    )
    current_run_rate = (
        float(state.current_run_rate) if state.current_run_rate is not None else 0.0
    )
    required_run_rate = (
        float(state.required_run_rate) if state.required_run_rate is not None else 0.0
    )

    if missing_rrr:
        target_pressure = 0.0
    else:
        target_pressure = required_run_rate / max(current_run_rate, 1.0)

    resources_remaining = _resources_remaining(
        balls_remaining=balls_remaining if not missing_balls else None,
        scheduled_balls=scheduled_balls if not missing_scheduled else None,
        wickets_remaining=wickets_remaining if not missing_wickets_remaining else None,
    )

    values = {
        "innings_number": float(state.innings_number or 0),
        "is_chase": 1.0 if is_chase_state(state) else 0.0,
        "is_first_innings": 1.0 if state.innings_number == 1 and not state.is_super_over else 0.0,
        "current_score": current_score,
        "wickets_lost": wickets_lost,
        "wickets_remaining": wickets_remaining,
        "legal_balls": legal_balls,
        "balls_remaining": balls_remaining,
        "scheduled_balls": scheduled_balls,
        "overs_remaining": overs_remaining,
        "target": target,
        "runs_remaining": runs_remaining,
        "current_run_rate": current_run_rate,
        "required_run_rate": required_run_rate,
        "target_pressure": target_pressure,
        "resources_remaining": resources_remaining,
        "runs_last_6": _sum_runs(recent_short),
        "runs_last_12": _sum_runs(recent_long),
        "wickets_last_6": _sum_counting_wickets(recent_short),
        "wickets_last_12": _sum_counting_wickets(recent_long),
        "boundaries_last_6": _sum_boundaries(recent_short),
        "boundaries_last_12": _sum_boundaries(recent_long),
        "missing_target": 1.0 if missing_target else 0.0,
        "missing_balls_remaining": 1.0 if missing_balls else 0.0,
        "missing_scheduled_balls": 1.0 if missing_scheduled else 0.0,
        "missing_current_run_rate": 1.0 if missing_crr else 0.0,
        "missing_required_run_rate": 1.0 if missing_rrr else 0.0,
        "missing_wickets_remaining": 1.0 if missing_wickets_remaining else 0.0,
    }

    if set(values) != set(FEATURE_NAMES):
        raise FeatureError("internal feature name mismatch")
    if any(not _is_finite(value) for value in values.values()):
        raise FeatureError(
            f"non-finite feature in {state.source_match_id}#{state.sequence}"
        )

    return FeatureVector(
        schema_version=FEATURE_SCHEMA_VERSION,
        source_match_id=state.source_match_id,
        sequence=state.sequence,
        values=values,
        missing={
            "target": missing_target,
            "balls_remaining": missing_balls,
            "scheduled_balls": missing_scheduled,
            "current_run_rate": missing_crr,
            "required_run_rate": missing_rrr,
            "wickets_remaining": missing_wickets_remaining,
        },
    )


def _window_delivery_states(
    current: MatchState,
    history: Sequence[MatchState],
) -> list[MatchState]:
    """Earlier same-innings deliveries plus the current ball when it is known.

    The current delivery is available at the prediction timestamp. Future
    deliveries are ignored even if they appear in ``history``.
    """

    window = [
        state
        for state in history
        if state.sequence < current.sequence
        and state.source_match_id == current.source_match_id
        and state.innings_number == current.innings_number
        and state.is_super_over == current.is_super_over
        and state.knowledge_horizon == KnowledgeHorizon.AT_DELIVERY
        and state.last_delivery is not None
        and not state.source_delivery_after_terminal
    ]
    if (
        current.last_delivery is not None
        and current.knowledge_horizon == KnowledgeHorizon.AT_DELIVERY
        and not current.source_delivery_after_terminal
    ):
        window.append(current)
    window.sort(key=lambda state: state.sequence)
    return window


def _sum_runs(states: Sequence[MatchState]) -> float:
    return float(sum(_delivery(state).total_runs for state in states))


def _sum_counting_wickets(states: Sequence[MatchState]) -> float:
    total = 0
    for state in states:
        total += sum(1 for wicket in _delivery(state).wickets if wicket.counts_as_wicket)
    return float(total)


def _sum_boundaries(states: Sequence[MatchState]) -> float:
    total = 0
    for state in states:
        if _is_boundary(_delivery(state)):
            total += 1
    return float(total)


def _delivery(state: MatchState) -> DeliveryApplied:
    if state.last_delivery is None:
        raise FeatureError("expected a delivery on a window state")
    return state.last_delivery


def _is_boundary(delivery: DeliveryApplied) -> bool:
    """Count 4 and 6 batter runs only when the source did not mark non_boundary.

    ``DeliveryApplied.non_boundary`` is copied from Cricsheet during replay.
    A four or six is not counted unless that flag is false. Missing source
    flags stay false, matching Cricsheet's convention that ``non_boundary``
    is present only for all-run fours and sixes.
    """

    if delivery.batter_runs not in {4, 6}:
        return False
    return not delivery.non_boundary


def _resources_remaining(
    *,
    balls_remaining: float | None,
    scheduled_balls: float | None,
    wickets_remaining: float | None,
) -> float:
    ball_frac: float | None = None
    if balls_remaining is not None and scheduled_balls and scheduled_balls > 0:
        ball_frac = max(0.0, min(1.0, balls_remaining / scheduled_balls))
    wicket_frac: float | None = None
    if wickets_remaining is not None:
        wicket_frac = max(
            0.0,
            min(1.0, wickets_remaining / float(STANDARD_WICKETS_TO_ALL_OUT)),
        )
    if ball_frac is None and wicket_frac is None:
        return 0.0
    if ball_frac is None:
        return float(wicket_frac)
    if wicket_frac is None:
        return float(ball_frac)
    return float(ball_frac * wicket_frac)


def _is_finite(value: float) -> bool:
    return value == value and value not in {float("inf"), float("-inf")}
