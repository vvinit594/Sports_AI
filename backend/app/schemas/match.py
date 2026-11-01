"""Normalized cricket match models produced from Cricsheet JSON."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceProvenance(FrozenModel):
    source: Literal["cricsheet"] = "cricsheet"
    source_match_id: str
    data_version: str
    created: str
    revision: int
    source_path: str | None = None


class TossInfo(FrozenModel):
    winner: str
    decision: str
    uncontested: bool | None = None


class OutcomeInfo(FrozenModel):
    winner: str | None = None
    result: str | None = None
    win_by_runs: int | None = None
    win_by_wickets: int | None = None
    win_by_innings: int | None = None
    method: str | None = None
    eliminator: str | None = None
    bowl_out_winner: str | None = None


class EventInfo(FrozenModel):
    name: str | None = None
    match_number: int | None = None
    group: str | None = None
    stage: str | None = None


class OfficialsInfo(FrozenModel):
    umpires: tuple[str, ...] = ()
    tv_umpires: tuple[str, ...] = ()
    reserve_umpires: tuple[str, ...] = ()
    match_referees: tuple[str, ...] = ()


class ExtraBreakdown(FrozenModel):
    wides: int = 0
    noballs: int = 0
    byes: int = 0
    legbyes: int = 0
    penalty: int = 0

    @property
    def total(self) -> int:
        return self.wides + self.noballs + self.byes + self.legbyes + self.penalty


class FielderInfo(FrozenModel):
    name: str


class WicketInfo(FrozenModel):
    kind: str
    player_out: str
    fielders: tuple[FielderInfo, ...] = ()
    counts_as_wicket: bool


class ReplacementInfo(FrozenModel):
    replacement_type: str
    player_in: str | None = None
    player_out: str | None = None
    reason: str | None = None
    role: str | None = None
    team: str | None = None


class ReviewInfo(FrozenModel):
    team: str
    batter: str
    decision: str
    umpire: str | None = None
    umpires_call: bool | None = None


class TargetInfo(FrozenModel):
    runs: int | None = None
    overs: int | float | None = None


class PenaltyRunsInfo(FrozenModel):
    pre: int = 0
    post: int = 0


class PowerplayInfo(FrozenModel):
    type: str
    start: float | int | None = None
    end: float | int | None = None


class MiscountedOverInfo(FrozenModel):
    over_number: int
    balls: int
    umpire: str | None = None


class NormalizedDelivery(FrozenModel):
    sequence: int
    innings_number: int
    innings_delivery_number: int
    over_number: int
    delivery_in_over: int
    actual_delivery: str | None
    batter: str
    bowler: str
    non_striker: str
    batter_runs: int
    extras_runs: int
    total_runs: int
    extras: ExtraBreakdown
    is_legal_delivery: bool
    is_wide: bool
    is_noball: bool
    is_bye: bool
    is_legbye: bool
    is_penalty: bool
    non_boundary: bool
    wickets: tuple[WicketInfo, ...] = ()
    replacements: tuple[ReplacementInfo, ...] = ()
    review: ReviewInfo | None = None


class NormalizedOver(FrozenModel):
    over_number: int
    deliveries: tuple[NormalizedDelivery, ...]


class NormalizedInnings(FrozenModel):
    innings_number: int
    batting_team: str
    bowling_team: str
    is_super_over: bool
    declared: bool = False
    forfeited: bool = False
    target: TargetInfo | None = None
    penalty_runs: PenaltyRunsInfo = Field(default_factory=PenaltyRunsInfo)
    absent_hurt: tuple[str, ...] = ()
    powerplays: tuple[PowerplayInfo, ...] = ()
    miscounted_overs: tuple[MiscountedOverInfo, ...] = ()
    overs: tuple[NormalizedOver, ...] = ()

    @property
    def deliveries(self) -> tuple[NormalizedDelivery, ...]:
        return tuple(delivery for over in self.overs for delivery in over.deliveries)


class MatchInfo(FrozenModel):
    balls_per_over: int
    match_type: str
    team_type: str | None = None
    gender: str
    scheduled_overs: int | None = None
    season: str
    dates: tuple[str, ...]
    teams: tuple[str, ...]
    venue: str | None = None
    city: str | None = None
    event: EventInfo | None = None
    toss: TossInfo
    outcome: OutcomeInfo
    players: dict[str, tuple[str, ...]]
    registry_people: dict[str, str] = Field(default_factory=dict)
    registry_venues: dict[str, str] = Field(default_factory=dict)
    player_of_match: tuple[str, ...] = ()
    officials: OfficialsInfo | None = None
    missing: tuple[Any, ...] = ()
    supersubs: dict[str, str] = Field(default_factory=dict)
    bowl_out: tuple[dict[str, str], ...] = ()


class NormalizedMatch(FrozenModel):
    provenance: SourceProvenance
    info: MatchInfo
    innings: tuple[NormalizedInnings, ...]

    @property
    def source_match_id(self) -> str:
        return self.provenance.source_match_id

    @property
    def deliveries(self) -> tuple[NormalizedDelivery, ...]:
        return tuple(
            delivery for innings in self.innings for delivery in innings.deliveries
        )

    def innings_by_number(self, innings_number: int) -> NormalizedInnings:
        for innings in self.innings:
            if innings.innings_number == innings_number:
                return innings
        raise KeyError(f"innings {innings_number} not found")
