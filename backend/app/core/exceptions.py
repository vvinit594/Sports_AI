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


class FeatureError(PulseIQError):
    """Raised when a match state cannot be turned into a feature vector."""


class DatasetError(PulseIQError):
    """Raised when a training dataset cannot be constructed safely."""


class InferenceError(PulseIQError):
    """Raised when win-probability inference is refused or invalid."""


class ModelRegistryError(PulseIQError):
    """Raised when a model artifact cannot be saved or loaded."""
