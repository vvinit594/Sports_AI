"""Validation report models for reconstructed match totals."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Issue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    innings_number: int | None = None
    sequence: int | None = None


class InningsValidation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    innings_number: int
    batting_team: str
    is_super_over: bool
    source_runs: int
    reconstructed_runs: int
    source_wicket_events: int
    reconstructed_wicket_events: int
    source_counting_wickets: int
    reconstructed_wickets: int
    source_legal_balls: int
    reconstructed_legal_balls: int
    source_deliveries: int
    reconstructed_deliveries: int
    source_target_runs: int | None
    reconstructed_target_runs: int | None


class ValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_match_id: str
    ok: bool
    innings: tuple[InningsValidation, ...]
    errors: tuple[Issue, ...] = Field(default_factory=tuple)
    warnings: tuple[Issue, ...] = Field(default_factory=tuple)
