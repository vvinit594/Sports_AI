"""Ball-by-ball reconstructed match state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import InningsPhase, TargetSource
from app.schemas.match import OutcomeInfo, WicketInfo


class DeliveryApplied(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int
    actual_delivery: str | None
    batter: str
    bowler: str
    non_striker: str
    batter_runs: int
    extras_runs: int
    total_runs: int
    is_legal_delivery: bool
    is_wide: bool
    is_noball: bool
    wickets: tuple[WicketInfo, ...] = ()


class MatchState(BaseModel):
    """State immediately after `sequence` deliveries have been applied.

    Sequence 0 is the empty pre-match state before the first ball.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_match_id: str
    sequence: int
    innings_number: int | None
    innings_phase: InningsPhase | None
    is_super_over: bool
    batting_team: str | None
    bowling_team: str | None

    innings_runs: int
    innings_wickets: int
    innings_wicket_events: int
    legal_balls: int
    total_deliveries: int
    overs: str

    current_run_rate: float | None
    scheduled_balls: int | None
    balls_remaining: int | None
    target: int | None
    target_source: TargetSource
    runs_remaining: int | None
    required_run_rate: float | None
    wickets_remaining: int | None

    last_delivery: DeliveryApplied | None = None
    innings_just_completed: bool = False
    match_complete: bool = False
    outcome: OutcomeInfo
    warnings: tuple[str, ...] = Field(default_factory=tuple)
