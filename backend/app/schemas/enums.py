"""Enumerations used by normalized match models."""

from __future__ import annotations

from enum import StrEnum


class TargetSource(StrEnum):
    CRICSHEET = "cricsheet"
    DERIVED_PREVIOUS_INNINGS = "derived_previous_innings"
    NONE = "none"


class InningsPhase(StrEnum):
    REGULATION = "regulation"
    SUPER_OVER = "super_over"
