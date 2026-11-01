"""Deterministic in-process replay of a historical cricket match."""

from __future__ import annotations

from app.core.exceptions import ReplayError
from app.schemas.match import NormalizedMatch
from app.schemas.state import MatchState
from app.services.match_engine.engine import MatchStateEngine


class ReplayEngine:
    """Replay a normalized match delivery by delivery.

    The same match always produces the same states. There is no live data
    and no randomness. Sequence 0 is the empty pre-match snapshot.
    """

    def __init__(self, match: NormalizedMatch):
        self.match = match
        self._engine = MatchStateEngine(match)
        self._states = self._engine.reconstruct()
        self._cursor = 0

    @property
    def states(self) -> tuple[MatchState, ...]:
        return tuple(self._states)

    @property
    def current(self) -> MatchState:
        return self._states[self._cursor]

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def total_deliveries(self) -> int:
        return len(self.match.deliveries)

    def restart(self) -> MatchState:
        self._cursor = 0
        return self.current

    def next(self) -> MatchState:
        if self._cursor >= len(self._states) - 1:
            raise ReplayError("replay is already at the final match state")
        self._cursor += 1
        return self.current

    def pause(self) -> MatchState:
        """Replay is pull-based; pause simply returns the current state."""

        return self.current

    def seek(self, sequence: int) -> MatchState:
        """Jump to the state after `sequence` deliveries."""

        for index, state in enumerate(self._states):
            if state.sequence == sequence and (
                index == 0 or self._states[index - 1].sequence != sequence
            ):
                self._cursor = index
                return self.current
        # Prefer the last state at this sequence if empty innings reused it.
        for index in range(len(self._states) - 1, -1, -1):
            if self._states[index].sequence == sequence:
                self._cursor = index
                return self.current
        raise ReplayError(f"no replay state at sequence {sequence}")

    def play_all(self) -> list[MatchState]:
        self._cursor = len(self._states) - 1
        return list(self._states)
