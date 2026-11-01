"""Domain exceptions for match parsing and reconstruction."""

from __future__ import annotations


class PulseIQError(Exception):
    """Base error for PulseIQ Phase 1 components."""


class ParseError(PulseIQError):
    """Raised when a Cricsheet document cannot be parsed safely."""


class MatchEngineError(PulseIQError):
    """Raised when match-state reconstruction cannot continue."""


class ReplayError(PulseIQError):
    """Raised when a replay command is invalid."""
