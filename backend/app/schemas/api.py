"""HTTP request and response contracts for the Phase 3 API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.match import OutcomeInfo
from app.schemas.state import MatchState


class FrozenApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ErrorResponse(FrozenApiModel):
    error: str
    code: str
    detail: str | None = None


class HealthResponse(FrozenApiModel):
    status: Literal["ok"] = "ok"
    service: str = "pulseiq"
    phase: int = 3


class ReadinessResponse(FrozenApiModel):
    status: Literal["ready", "not_ready"]
    catalog_loaded: bool
    match_count: int
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    model_loaded: bool
    llm_provider: str
    llm_configured: bool


class MatchSummary(FrozenApiModel):
    source_match_id: str
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    teams: tuple[str, ...]
    dates: tuple[str, ...]
    venue: str | None = None
    city: str | None = None
    match_type: str
    gender: str
    season: str
    event_name: str | None = None
    outcome: OutcomeInfo
    innings_count: int
    delivery_count: int
    is_historical: bool = True


class MatchDetail(MatchSummary):
    balls_per_over: int
    scheduled_overs: int | None = None
    toss_winner: str | None = None
    toss_decision: str | None = None
    player_of_match: tuple[str, ...] = ()
    latest_sequence: int


class MatchListResponse(FrozenApiModel):
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    count: int
    matches: list[MatchSummary]


class MatchStateResponse(FrozenApiModel):
    source_match_id: str
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    requested_sequence: int | None = None
    latest_sequence: int
    state: MatchState
    states: list[MatchState] | None = None


class ModelMetadataView(FrozenApiModel):
    model_id: str
    model_kind: str
    feature_schema_version: str
    evaluation_is_meaningful: bool
    evaluation_limitation: str | None = None
    trained_at: str
    n_train_rows: int = 0
    fitted_split: str = "train"
    validation_role: str = "diagnostic_only"
    notes: tuple[str, ...] = ()


class ProbabilityPredictionView(FrozenApiModel):
    source_match_id: str
    sequence: int
    probability: float
    model_id: str
    feature_schema_version: str


class WinProbabilityResponse(FrozenApiModel):
    source_match_id: str
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    available: bool
    unavailable_reason: str | None = None
    requested_sequence: int | None = None
    predictions: list[ProbabilityPredictionView] = Field(default_factory=list)
    model: ModelMetadataView | None = None


class MomentView(FrozenApiModel):
    moment_type: str
    source_match_id: str
    sequence: int
    probability_before: float
    probability_after: float
    probability_change: float
    reasons: tuple[str, ...]
    match_context: dict[str, Any] = Field(default_factory=dict)


class MomentsResponse(FrozenApiModel):
    source_match_id: str
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    available: bool
    unavailable_reason: str | None = None
    count: int
    moments: list[MomentView] = Field(default_factory=list)
    model: ModelMetadataView | None = None
