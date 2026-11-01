"""Regression tests for the final Phase 1 edge-case audit."""

from __future__ import annotations

import pytest

from app.core.exceptions import ParseError
from app.schemas.enums import InningsCompletionReason, KnowledgeHorizon, MatchCompletionReason
from app.services.ingestion import parse_cricsheet_dict
from app.services.match_engine import MatchStateEngine
from tests.helpers import cricsheet_match, delivery, innings, over


def _states(raw, match_id="audit"):
    match = parse_cricsheet_dict(raw, source_match_id=match_id)
    return match, MatchStateEngine(match).reconstruct()


def test_terminal_score_is_frozen_while_source_totals_continue():
    raw = cricsheet_match(
        [
            innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=6)])]),
            innings(
                "Beta",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=4),
                            delivery(actual_delivery="0.2", batter_runs=1),
                            delivery(actual_delivery="0.3", batter_runs=2),
                        ],
                    )
                ],
                target={"overs": 20, "runs": 4},
            ),
        ]
    )
    _, states = _states(raw, "terminal-snapshot")
    chase = [state for state in states if state.innings_number == 2 and state.last_delivery]
    winning = next(state for state in chase if state.innings_just_completed)
    later = [state for state in chase if state.source_delivery_after_terminal]
    final = chase[-1]

    assert winning.terminal_innings_runs == 4
    assert winning.innings_runs_at_delivery == 4
    assert winning.is_active_prediction_state is False
    assert later
    assert all(state.terminal_innings_runs == 4 for state in later)
    assert all(state.innings_runs_at_delivery > 4 for state in later)
    assert final.innings_runs == 7
    assert final.terminal_innings_runs == 4
    assert final.terminal_sequence == winning.sequence
    assert final.innings_completion_reason == InningsCompletionReason.TARGET_REACHED


def test_post_penalty_does_not_reclassify_a_completed_or_failed_chase():
    raw = cricsheet_match(
        [
            innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=6)])]),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=2)])],
                target={"overs": "0.1", "runs": 8},
                penalty_runs={"post": 10},
            ),
        ]
    )
    _, states = _states(raw, "post-penalty-chase")
    final = [state for state in states if state.innings_number == 2][-1]
    assert final.innings_runs == 12
    assert final.innings_runs_at_delivery == 2
    assert final.terminal_innings_runs == 2
    assert final.innings_completion_reason == InningsCompletionReason.OVERS_EXHAUSTED
    assert final.includes_post_innings_penalty is True
    assert final.knowledge_horizon == KnowledgeHorizon.AFTER_INNINGS
    assert final.runs_remaining == 6
    assert final.is_active_prediction_state is False


def test_zero_available_wickets_is_all_out_before_any_ball():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
                absent_hurt=[f"Injured {index}" for index in range(10)],
            )
        ]
    )
    _, states = _states(raw, "no-pair")
    opening = states[0]
    delivery_state = next(state for state in states if state.last_delivery)
    final = states[-1]
    assert opening.innings_completion_reason == InningsCompletionReason.ALL_OUT
    assert opening.terminal_innings_runs == 0
    assert opening.is_active_prediction_state is False
    assert delivery_state.source_delivery_after_terminal is True
    assert delivery_state.terminal_innings_runs == 0
    assert delivery_state.innings_runs_at_delivery == 1
    assert final.innings_completion_reason == InningsCompletionReason.ALL_OUT
    assert final.match_complete is True


def test_forfeit_completes_innings_not_always_the_match():
    raw = cricsheet_match(
        [
            innings("Alpha", [], forfeited=True),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
                target={"overs": 20, "runs": 1},
            ),
        ]
    )
    _, states = _states(raw, "forfeit-first")
    forfeited = [state for state in states if state.innings_number == 1][-1]
    chase = [state for state in states if state.innings_number == 2 and state.last_delivery][-1]
    assert forfeited.innings_completion_reason == InningsCompletionReason.FORFEITED
    assert forfeited.innings_complete is True
    assert forfeited.match_complete is False
    assert chase.innings_number == 2
    assert chase.match_complete is True

    last_only = cricsheet_match([innings("Alpha", [], forfeited=True)])
    _, last_states = _states(last_only, "forfeit-last")
    final = last_states[-1]
    assert final.innings_completion_reason == InningsCompletionReason.FORFEITED
    assert final.match_complete is True
    assert final.match_completion_reason == MatchCompletionReason.LAST_INNINGS_COMPLETE


def test_fractional_integers_are_rejected():
    raw = cricsheet_match([innings("Alpha", [over(0, [delivery(actual_delivery="0.1")])])])
    raw["innings"][0]["overs"][0]["deliveries"][0]["runs"] = {
        "batter": 1.5,
        "extras": 0,
        "total": 1.5,
    }
    with pytest.raises(ParseError, match="must be an integer"):
        parse_cricsheet_dict(raw, source_match_id="frac-runs")

    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [over(0, [delivery(actual_delivery="0.1", extras_runs=1, extras={"wides": 1})])],
            )
        ]
    )
    raw["innings"][0]["overs"][0]["deliveries"][0]["extras"] = {"wides": 1.5}
    with pytest.raises(ParseError, match="must be an integer"):
        parse_cricsheet_dict(raw, source_match_id="frac-extra")

    raw = cricsheet_match([innings("Alpha", [over(0, [delivery(actual_delivery="0.1")])])])
    raw["meta"]["revision"] = 1.5
    with pytest.raises(ParseError, match="must be an integer"):
        parse_cricsheet_dict(raw, source_match_id="frac-revision")


def test_whole_float_integers_are_accepted():
    raw = cricsheet_match([innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])])])
    raw["innings"][0]["overs"][0]["deliveries"][0]["runs"] = {
        "batter": 1.0,
        "extras": 0.0,
        "total": 1.0,
    }
    match = parse_cricsheet_dict(raw, source_match_id="whole-float")
    assert match.deliveries[0].batter_runs == 1


def test_actual_delivery_allows_wides_and_miscounts_but_rejects_over_mismatch():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", extras_runs=1, extras={"wides": 1}),
                            delivery(actual_delivery="0.1", batter_runs=0),
                        ],
                    ),
                    over(
                        1,
                        [
                            delivery(actual_delivery="1.7"),
                        ],
                    ),
                ],
            )
        ]
    )
    match = parse_cricsheet_dict(raw, source_match_id="labels-ok")
    assert [item.actual_delivery for item in match.deliveries] == ["0.1", "0.1", "1.7"]
    assert match.deliveries[0].is_legal_delivery is False
    assert match.deliveries[1].is_legal_delivery is True

    raw["innings"][0]["overs"][0]["deliveries"][0]["actual_delivery"] = "3.1"
    with pytest.raises(ParseError, match="does not match over"):
        parse_cricsheet_dict(raw, source_match_id="label-mismatch")
