"""Pure cricket rules used during parsing and state reconstruction.

The functions here do not invent missing source fields. They only apply
documented cricket rules to values that already exist in a match record.
"""

from __future__ import annotations

from app.core.constants import (
    DEFAULT_BALLS_PER_OVER,
    DEFAULT_T20_OVERS,
    ILLEGAL_EXTRA_TYPES,
    KNOWN_COUNTING_DISMISSALS,
    NON_COUNTING_DISMISSALS,
    STANDARD_WICKETS_TO_ALL_OUT,
    SUPER_OVER_SCHEDULED_OVERS,
    T20_MATCH_TYPES,
)


def is_legal_delivery(extras: dict[str, int] | None) -> bool:
    """A delivery is legal unless it is a wide or a no-ball.

    Byes, leg-byes, and penalty extras do not make a delivery illegal.
    A wicket can occur on a wide or no-ball; that does not make it legal.
    """

    if not extras:
        return True
    return not any(extra_type in extras for extra_type in ILLEGAL_EXTRA_TYPES)


def counts_as_wicket(kind: str | None) -> bool:
    """Return whether a dismissal counts toward all-out.

    Unknown kinds are treated as counting wickets so a new dismissal type
    cannot silently under-count all-out. Callers should record a warning.
    """

    if kind is None:
        return True
    normalized = kind.strip().lower()
    if normalized in NON_COUNTING_DISMISSALS:
        return False
    return True


def is_known_dismissal_kind(kind: str | None) -> bool:
    if kind is None:
        return False
    normalized = kind.strip().lower()
    return normalized in KNOWN_COUNTING_DISMISSALS or normalized in NON_COUNTING_DISMISSALS


def overs_notation_to_balls(
    value: int | float | str | None,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
) -> int | None:
    """Convert cricket overs notation to legal balls.

    Cricsheet target overs use cricket notation, not decimal overs:
    20 -> 120 balls, 6 -> 36 balls, 35.1 -> 35 overs + 1 ball = 211 balls.
    """

    if value is None:
        return None
    if balls_per_over <= 0:
        raise ValueError("balls_per_over must be positive")

    text = str(value).strip()
    if not text:
        return None
    if "." in text:
        overs_text, balls_text = text.split(".", 1)
        return int(overs_text) * balls_per_over + int(balls_text)
    return int(float(text)) * balls_per_over


def balls_to_overs_notation(
    legal_balls: int,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
) -> str:
    """Convert completed legal balls to cricket overs notation."""

    if legal_balls < 0:
        raise ValueError("legal_balls cannot be negative")
    if balls_per_over <= 0:
        raise ValueError("balls_per_over must be positive")
    overs, balls = divmod(legal_balls, balls_per_over)
    return f"{overs}.{balls}"


def current_run_rate(
    runs: int,
    legal_balls: int,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
) -> float | None:
    if legal_balls <= 0:
        return None
    return (runs / legal_balls) * balls_per_over


def required_run_rate(
    runs_remaining: int | None,
    balls_remaining: int | None,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
) -> float | None:
    if runs_remaining is None or balls_remaining is None:
        return None
    if runs_remaining <= 0:
        return 0.0
    if balls_remaining <= 0:
        return None
    return (runs_remaining / balls_remaining) * balls_per_over


def max_wickets_available(absent_hurt_count: int = 0) -> int:
    """Standard T20 all-out is 10 wickets, reduced by absent-hurt players.

    Squad size is not used because Cricsheet player lists can include
    substitutes who are not part of the starting eleven.
    """

    return max(0, STANDARD_WICKETS_TO_ALL_OUT - max(0, absent_hurt_count))


def scheduled_balls_for_innings(
    *,
    target_overs: int | float | str | None,
    is_super_over: bool,
    match_overs: int | None,
    match_type: str | None,
    balls_per_over: int = DEFAULT_BALLS_PER_OVER,
) -> int | None:
    """Determine how many legal balls are scheduled for an innings.

    Preference order:
    1. Source target.overs when present.
    2. One over for a super over.
    3. Match-level scheduled overs.
    4. 20 overs for T20 / IT20 if match overs are missing.
    """

    from_target = overs_notation_to_balls(target_overs, balls_per_over)
    if from_target is not None:
        return from_target
    if is_super_over:
        return SUPER_OVER_SCHEDULED_OVERS * balls_per_over
    if match_overs is not None:
        return match_overs * balls_per_over
    if match_type in T20_MATCH_TYPES:
        return DEFAULT_T20_OVERS * balls_per_over
    return None
