"""Cricket constants used by the Phase 1 match engine.

These values are cricket-standard defaults. Match-specific values from
Cricsheet (balls_per_over, scheduled overs, listed players) take priority.
"""

from __future__ import annotations

DEFAULT_BALLS_PER_OVER = 6
DEFAULT_T20_OVERS = 20
DEFAULT_PLAYERS_PER_SIDE = 11
STANDARD_WICKETS_TO_ALL_OUT = 10
SUPER_OVER_SCHEDULED_OVERS = 1

SOURCE_NAME = "cricsheet"

ILLEGAL_EXTRA_TYPES = frozenset({"wides", "noballs"})
KNOWN_EXTRA_TYPES = frozenset({"wides", "noballs", "byes", "legbyes", "penalty"})

# Dismissals that remove a batter but do not count toward all-out.
NON_COUNTING_DISMISSALS = frozenset(
    {
        "retired hurt",
        "retired not out",
    }
)

# Dismissals observed in Cricsheet T20 data plus documented kinds.
KNOWN_COUNTING_DISMISSALS = frozenset(
    {
        "bowled",
        "caught",
        "caught and bowled",
        "lbw",
        "stumped",
        "run out",
        "hit wicket",
        "obstructing the field",
        "hit the ball twice",
        "handled the ball",
        "timed out",
        "retired out",
    }
)

T20_MATCH_TYPES = frozenset({"T20", "IT20"})
