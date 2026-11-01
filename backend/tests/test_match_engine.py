import pytest

from app.schemas.enums import TargetSource
from app.services.ingestion import parse_cricsheet_dict
from app.services.match_engine import MatchStateEngine
from tests.helpers import cricsheet_match, delivery, innings, over


def _states(raw, match_id="synthetic"):
    match = parse_cricsheet_dict(raw, source_match_id=match_id)
    return match, MatchStateEngine(match).reconstruct()


def test_wide_does_not_increment_legal_balls_but_adds_runs():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=1),
                            delivery(actual_delivery="0.2", extras_runs=1, extras={"wides": 1}),
                            delivery(actual_delivery="0.2", batter_runs=0),
                        ],
                    )
                ],
            )
        ]
    )
    _, states = _states(raw, "wide")
    final = states[-1]
    assert final.innings_runs == 2
    assert final.legal_balls == 2
    assert final.total_deliveries == 3
    assert final.overs == "0.2"


def test_noball_is_illegal_and_can_include_bat_runs():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(
                                actual_delivery="0.1",
                                batter_runs=4,
                                extras_runs=1,
                                extras={"noballs": 1},
                            )
                        ],
                    )
                ],
            )
        ]
    )
    _, states = _states(raw, "noball")
    final = states[-1]
    assert final.innings_runs == 5
    assert final.legal_balls == 0
    assert final.overs == "0.0"


def test_wicket_on_wide_counts_wicket_but_not_legal_ball():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(
                                actual_delivery="0.1",
                                extras_runs=1,
                                extras={"wides": 1},
                                wickets=[{"kind": "stumped", "player_out": "A Batter"}],
                            )
                        ],
                    )
                ],
            )
        ]
    )
    _, states = _states(raw, "wide-wicket")
    final = states[-1]
    assert final.innings_wickets == 1
    assert final.legal_balls == 0
    assert final.total_deliveries == 1


def test_retired_hurt_does_not_count_as_wicket():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(
                                actual_delivery="0.1",
                                batter_runs=1,
                                wickets=[{"kind": "retired hurt", "player_out": "A Batter"}],
                            ),
                            delivery(
                                actual_delivery="0.2",
                                wickets=[{"kind": "retired out", "player_out": "C Partner"}],
                            ),
                        ],
                    )
                ],
            )
        ]
    )
    _, states = _states(raw, "retire")
    final = states[-1]
    assert final.innings_wicket_events == 2
    assert final.innings_wickets == 1
    assert final.wickets_remaining == 9


def test_absent_hurt_reduces_wickets_remaining():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(
                                actual_delivery="0.1",
                                wickets=[{"kind": "bowled", "player_out": "A Batter"}],
                            )
                        ],
                    )
                ],
                absent_hurt=["Injured Player"],
            )
        ]
    )
    _, states = _states(raw, "absent")
    assert states[-1].wickets_remaining == 8


def test_target_and_required_rate_use_source_target():
    raw = cricsheet_match(
        [
            innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=6)] * 6)]),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
                target={"overs": 20, "runs": 8},
            ),
        ]
    )
    match, states = _states(raw, "chase")
    chase = [state for state in states if state.innings_number == 2 and state.sequence > 0][-1]
    assert chase.target == 8
    assert chase.target_source == TargetSource.CRICSHEET
    assert chase.runs_remaining == 7
    assert chase.balls_remaining == 119
    assert chase.required_run_rate == pytest.approx((7 / 119) * 6)
    assert match.innings[0].target is None


def test_required_run_rate_calculation_explicit():
    raw = cricsheet_match(
        [
            innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=2)])],
                target={"overs": 1, "runs": 8},
            ),
        ],
        overs=1,
    )
    _, states = _states(raw, "rrr")
    chase = [state for state in states if state.innings_number == 2 and state.last_delivery][-1]
    assert chase.runs_remaining == 6
    assert chase.balls_remaining == 5
    assert chase.required_run_rate == pytest.approx(7.2)
    assert chase.current_run_rate == pytest.approx(12.0)


def test_super_over_is_isolated_and_can_derive_chase_target():
    raw = cricsheet_match(
        [
            innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=4)])]),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=4)])],
                target={"overs": 20, "runs": 5},
            ),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=6)])],
                super_over=True,
            ),
            innings(
                "Alpha",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
                super_over=True,
            ),
        ],
        outcome={"result": "tie", "eliminator": "Beta"},
    )
    _, states = _states(raw, "super")
    first = [state for state in states if state.innings_number == 1 and state.innings_just_completed][-1]
    second = [state for state in states if state.innings_number == 2 and state.innings_just_completed][-1]
    so_one = [state for state in states if state.innings_number == 3 and state.innings_just_completed][-1]
    so_two = [state for state in states if state.innings_number == 4 and state.innings_just_completed][-1]
    assert first.innings_runs == 4
    assert second.innings_runs == 4
    assert so_one.is_super_over is True
    assert so_one.target is None
    assert so_one.scheduled_balls == 6
    assert so_two.target == 7
    assert so_two.target_source == TargetSource.DERIVED_PREVIOUS_INNINGS
    assert so_two.runs_remaining == 6


def test_penalty_pre_and_post_are_applied_without_being_deliveries():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
                penalty_runs={"pre": 5, "post": 6},
            )
        ]
    )
    _, states = _states(raw, "penalty")
    assert states[0].innings_runs == 5
    assert states[-1].innings_runs == 12
    assert states[-1].total_deliveries == 1


def test_dl_target_overs_shorten_balls_remaining():
    raw = cricsheet_match(
        [
            innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=10)])]),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=4)])],
                target={"overs": 6, "runs": 48},
            ),
        ],
        outcome={"winner": "Beta", "by": {"wickets": 7}, "method": "D/L"},
    )
    _, states = _states(raw, "dl")
    chase = [state for state in states if state.innings_number == 2 and state.last_delivery][-1]
    assert chase.target == 48
    assert chase.scheduled_balls == 36
    assert chase.balls_remaining == 35


def test_one_innings_no_result_has_no_target():
    raw = cricsheet_match(
        [innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])])],
        outcome={"result": "no result"},
    )
    _, states = _states(raw, "no-result")
    final = states[-1]
    assert final.target is None
    assert final.runs_remaining is None
    assert final.match_complete is True
    assert len([state for state in states if state.innings_number == 2]) == 0
