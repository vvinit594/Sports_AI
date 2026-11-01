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


class KnowledgeHorizon(StrEnum):
    """What information this state is allowed to include."""

    PRE_INNINGS = "pre_innings"
    AT_DELIVERY = "at_delivery"
    AFTER_INNINGS = "after_innings"


class InningsCompletionReason(StrEnum):
    TARGET_REACHED = "target_reached"
    ALL_OUT = "all_out"
    OVERS_EXHAUSTED = "overs_exhausted"
    DECLARED = "declared"
    FORFEITED = "forfeited"
    SOURCE_ENDED = "source_ended"


class MatchCompletionReason(StrEnum):
    TARGET_REACHED = "target_reached"
    LAST_INNINGS_COMPLETE = "last_innings_complete"
    SOURCE_ENDED = "source_ended"
    NO_INNINGS = "no_innings"
