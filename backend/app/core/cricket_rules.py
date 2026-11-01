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
    20 -> 120 balls, 19.5 -> 119 balls, 35.1 -> 35 overs + 1 ball = 211 balls.

    The ball component must be strictly less than ``balls_per_over``.
    ``5.6`` is therefore invalid for a six-ball over; six legal balls are ``6.0``.
    """

    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"malformed overs notation: {value!r}")
    if balls_per_over <= 0:
        raise ValueError("balls_per_over must be positive")

    text = _overs_notation_text(value)
    if text is None:
        return None

    if "." in text:
        overs_text, balls_text = text.split(".", 1)
        if not overs_text or not balls_text or not _is_int_token(overs_text) or not _is_int_token(balls_text):
            raise ValueError(f"malformed overs notation: {value!r}")
        overs = int(overs_text)
        balls = int(balls_text)
        if overs < 0 or balls < 0:
            raise ValueError(f"negative overs notation is invalid: {value!r}")
        if balls >= balls_per_over:
            raise ValueError(
                f"invalid cricket overs notation {value!r}: ball component {balls} "
                f"must be less than {balls_per_over}"
            )
        return overs * balls_per_over + balls

    if not _is_int_token(text):
        raise ValueError(f"malformed overs notation: {value!r}")
    overs = int(text)
    if overs < 0:
        raise ValueError(f"negative overs notation is invalid: {value!r}")
    return overs * balls_per_over


def _overs_notation_text(value: int | float | str) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:  # NaN
            raise ValueError(f"malformed overs notation: {value!r}")
        return format(value, ".10f").rstrip("0").rstrip(".")
    raise ValueError(f"malformed overs notation: {value!r}")


def _is_int_token(text: str) -> bool:
    if text.startswith("-"):
        return len(text) > 1 and text[1:].isdigit()
    return text.isdigit()


def target_reached(innings_runs: int, target: int | None) -> bool:
    return target is not None and innings_runs >= target


def innings_is_all_out(innings_wickets: int, absent_hurt_count: int = 0) -> bool:
    """Return whether the batting side can no longer continue.

    All-out is ``wickets_lost >= available_wickets``. If ten or more players
    are absent hurt, available wickets are 0: no batting pair can be formed,
    so the innings is all-out immediately.
    """

    available = max_wickets_available(absent_hurt_count)
    return innings_wickets >= available


def scheduled_balls_exhausted(legal_balls: int, scheduled_balls: int | None) -> bool:
    return scheduled_balls is not None and legal_balls >= scheduled_balls


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
