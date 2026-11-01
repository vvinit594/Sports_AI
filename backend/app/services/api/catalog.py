"""Historical match catalog for the API.

The current data source is local Cricsheet sample files. The catalog interface
is intentionally provider-shaped so a future live feed can implement the same
lookup methods without changing API contracts. Historical files are not live
matches.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import CatalogError, ParseError
from app.schemas.api import MatchDetail, MatchSummary
from app.schemas.match import NormalizedMatch
from app.schemas.state import MatchState
from app.services.ingestion import parse_cricsheet_file
from app.services.match_engine import MatchStateEngine

logger = logging.getLogger(__name__)

DATA_SOURCE = "historical_cricsheet"


@dataclass(frozen=True)
class LoadedMatch:
    match: NormalizedMatch
    states: tuple[MatchState, ...]

    @property
    def source_match_id(self) -> str:
        return self.match.source_match_id

    @property
    def latest_state(self) -> MatchState:
        return self.states[-1]

    def state_at(self, sequence: int | None = None) -> MatchState:
        if sequence is None:
            return self.latest_state
        for index, state in enumerate(self.states):
            if state.sequence == sequence and (
                index == 0 or self.states[index - 1].sequence != sequence
            ):
                return state
        for state in reversed(self.states):
            if state.sequence == sequence:
                return state
        raise CatalogError(
            f"no match state at sequence {sequence}",
            code="sequence_not_found",
            status_code=404,
        )


class MatchCatalog:
    """In-memory index of reconstructed historical matches."""

    def __init__(self, loaded: Sequence[LoadedMatch], *, directory: Path | None = None):
        self.directory = directory
        self._by_id = {item.source_match_id: item for item in loaded}
        self._order = tuple(item.source_match_id for item in loaded)

    @classmethod
    def from_directory(cls, directory: Path) -> MatchCatalog:
        path = Path(directory)
        loaded: list[LoadedMatch] = []
        if not path.exists() or not path.is_dir():
            logger.warning("cricsheet directory is missing: %s", path)
            return cls((), directory=path)
        for file_path in sorted(path.glob("*.json")):
            try:
                match = parse_cricsheet_file(file_path)
                states = tuple(MatchStateEngine(match).reconstruct())
            except (ParseError, OSError) as exc:
                logger.warning(
                    "skipped unreadable match file %s: %s", file_path.name, exc
                )
                continue
            loaded.append(LoadedMatch(match=match, states=states))
        logger.info("loaded %s historical matches from %s", len(loaded), path)
        return cls(loaded, directory=path)

    @classmethod
    def from_matches(cls, matches: Sequence[NormalizedMatch]) -> MatchCatalog:
        loaded = [
            LoadedMatch(
                match=match,
                states=tuple(MatchStateEngine(match).reconstruct()),
            )
            for match in matches
        ]
        return cls(loaded)

    def ready(self) -> bool:
        return self.directory is None or (
            self.directory.exists() and self.directory.is_dir()
        )

    def count(self) -> int:
        return len(self._order)

    def get(self, match_id: str) -> LoadedMatch:
        loaded = self._by_id.get(match_id)
        if loaded is None:
            raise CatalogError(f"match not found: {match_id}")
        return loaded

    def list_summaries(self) -> list[MatchSummary]:
        return [to_summary(self._by_id[match_id]) for match_id in self._order]


def to_summary(loaded: LoadedMatch) -> MatchSummary:
    info = loaded.match.info
    event_name = info.event.name if info.event is not None else None
    return MatchSummary(
        source_match_id=loaded.source_match_id,
        teams=info.teams,
        dates=info.dates,
        venue=info.venue,
        city=info.city,
        match_type=info.match_type,
        gender=info.gender,
        season=str(info.season),
        event_name=event_name,
        outcome=info.outcome,
        innings_count=len(loaded.match.innings),
        delivery_count=len(loaded.match.deliveries),
        is_historical=True,
    )


def to_detail(loaded: LoadedMatch) -> MatchDetail:
    summary = to_summary(loaded)
    info = loaded.match.info
    toss = info.toss
    return MatchDetail(
        **summary.model_dump(),
        balls_per_over=info.balls_per_over,
        scheduled_overs=info.scheduled_overs,
        toss_winner=toss.winner if toss is not None else None,
        toss_decision=toss.decision if toss is not None else None,
        player_of_match=info.player_of_match,
        latest_sequence=loaded.latest_state.sequence,
    )
