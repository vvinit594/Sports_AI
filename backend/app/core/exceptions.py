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


class IntelligenceError(PulseIQError):
    """Raised when match-intelligence inputs are invalid."""


class CatalogError(PulseIQError):
    """Raised when a historical match cannot be loaded for the API."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "match_not_found",
        status_code: int = 404,
    ):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class ExplanationError(PulseIQError):
    """Raised when an explanation cannot be produced from supplied evidence."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "explanation_error",
        status_code: int = 400,
    ):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class ProviderError(ExplanationError):
    """Raised when the configured LLM provider fails."""

    def __init__(
        self, message: str, *, code: str = "provider_error", status_code: int = 502
    ):
        super().__init__(message, code=code, status_code=status_code)
