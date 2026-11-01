"""Explanation request, grounded context, and structured LLM output."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FrozenExplanationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AudienceLevel(StrEnum):
    BEGINNER = "beginner"
    CASUAL = "casual"
    ADVANCED = "advanced"


class ExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience_level: AudienceLevel
    sequence: int | None = Field(
        default=None,
        ge=0,
        description="Delivery sequence to explain. Omit for the latest reconstructed state.",
    )


class DeliverySnippet(FrozenExplanationModel):
    sequence: int
    actual_delivery: str | None = None
    batter: str | None = None
    bowler: str | None = None
    non_striker: str | None = None
    total_runs: int | None = None
    batter_runs: int | None = None
    extras_runs: int | None = None
    is_legal_delivery: bool | None = None
    is_wide: bool | None = None
    is_noball: bool | None = None
    wicket_kinds: tuple[str, ...] = ()


class WinProbabilityEvidence(FrozenExplanationModel):
    probability: float
    model_id: str
    model_kind: str
    feature_schema_version: str
    evaluation_is_meaningful: bool
    evaluation_limitation: str | None = None


class MomentEvidence(FrozenExplanationModel):
    moment_type: str
    sequence: int
    probability_before: float | None = None
    probability_after: float | None = None
    probability_change: float | None = None
    reasons: tuple[str, ...] = ()


class ExplanationContext(FrozenExplanationModel):
    """Validated evidence passed to the LLM. Missing values stay null."""

    source_match_id: str
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    teams: tuple[str, ...]
    batting_team: str | None = None
    bowling_team: str | None = None
    innings_number: int | None = None
    innings_phase: str | None = None
    score: int | None = None
    wickets: int | None = None
    overs: str | None = None
    legal_balls: int | None = None
    target: int | None = None
    runs_remaining: int | None = None
    wickets_remaining: int | None = None
    balls_remaining: int | None = None
    required_run_rate: float | None = None
    current_run_rate: float | None = None
    sequence: int
    last_delivery: DeliverySnippet | None = None
    recent_deliveries: tuple[DeliverySnippet, ...] = ()
    significant_moments: tuple[MomentEvidence, ...] = ()
    win_probability: WinProbabilityEvidence | None = None
    is_active_prediction_state: bool
    innings_complete: bool
    match_complete: bool
    unknown_fields: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class LLMExplanationPayload(FrozenExplanationModel):
    """Fields the LLM is allowed to generate. Identity fields are filled by the service."""

    summary: str
    what_happened: str
    why_it_matters: str
    match_context: str
    key_factors: tuple[str, ...] = ()

    @field_validator(
        "summary", "what_happened", "why_it_matters", "match_context", mode="before"
    )
    @classmethod
    def _require_text(cls, value: object) -> object:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("explanation text fields must be non-empty")
        return value.strip()

    @field_validator("key_factors", mode="before")
    @classmethod
    def _clean_factors(cls, value: object) -> object:
        if value is None:
            return ()
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError("key_factors must be a list of strings")
        cleaned = tuple(
            item.strip() for item in value if isinstance(item, str) and item.strip()
        )
        return cleaned


class ExplanationResponse(FrozenExplanationModel):
    summary: str
    what_happened: str
    why_it_matters: str
    match_context: str
    key_factors: tuple[str, ...]
    audience_level: AudienceLevel
    source_match_id: str
    source_sequence: int
    generated_at: datetime
    model_provider: str
    model_name: str
    data_source: Literal["historical_cricsheet"] = "historical_cricsheet"
    grounded: bool = True
