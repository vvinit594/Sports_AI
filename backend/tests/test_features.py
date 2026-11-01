from app.core.exceptions import FeatureError
from app.services.ingestion import parse_cricsheet_dict
from app.services.match_engine import MatchStateEngine
from app.services.ml.features import (
    FEATURE_NAMES,
    extract_feature_vector,
    is_active_feature_state,
    is_chase_training_state,
)
from tests.helpers import cricsheet_match, delivery, innings, over
from tests.ml_helpers import two_innings_chase


def test_chase_features_use_only_information_at_current_ball():
    match, states = two_innings_chase(
        match_id="feat-leak",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 4, 0, 0],
        winner="Beta",
    )
    chase = [
        state
        for state in states
        if is_chase_training_state(state) and state.last_delivery is not None
    ]
    third_single = [state for state in chase if state.last_delivery.batter_runs == 1][2]
    features = extract_feature_vector(
        third_single, states, match=match, balls_per_over=6
    )
    assert features.values["runs_last_6"] == 3.0
    assert features.values["boundaries_last_6"] == 0.0
    assert features.values["current_score"] == 3.0
    later = next(
        state
        for state in states
        if state.last_delivery is not None and state.last_delivery.batter_runs == 4
    )
    assert later.sequence > third_single.sequence


def test_future_history_rows_are_ignored():
    match, states = two_innings_chase(
        match_id="feat-future",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 4],
        winner="Beta",
    )
    chase = [
        state
        for state in states
        if is_chase_training_state(state) and state.last_delivery is not None
    ]
    current = chase[1]
    leaked = extract_feature_vector(current, states, match=match)
    assert leaked.values["runs_last_6"] == 2.0
    assert leaked.values["current_score"] == 2.0


def test_missing_target_on_first_innings_is_explicit():
    match, states = two_innings_chase(
        match_id="feat-missing",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1],
        winner="Beta",
    )
    first = next(
        state
        for state in states
        if state.innings_number == 1
        and is_active_feature_state(state)
        and state.last_delivery
    )
    features = extract_feature_vector(first, states, match=match)
    assert features.values["missing_target"] == 1.0
    assert features.values["missing_required_run_rate"] == 1.0
    assert features.values["is_first_innings"] == 1.0
    assert features.values["is_chase"] == 0.0
    assert features.is_complete(FEATURE_NAMES)


def test_terminal_states_are_not_active_feature_states():
    _, states = two_innings_chase(
        match_id="feat-terminal",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 4],
        winner="Beta",
    )
    terminal = [
        state for state in states if state.innings_complete or state.match_complete
    ]
    assert terminal
    assert all(not is_chase_training_state(state) for state in terminal)
    active = [state for state in states if is_chase_training_state(state)]
    assert active
    assert all(state.innings_runs_at_delivery < state.target for state in active)


def test_extract_rejects_inactive_states():
    _, states = two_innings_chase(
        match_id="feat-inactive",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[7],
        winner="Beta",
    )
    finished = next(state for state in states if state.innings_complete)
    try:
        extract_feature_vector(finished, states)
    except FeatureError as exc:
        assert "not an active prediction state" in str(exc)
    else:
        raise AssertionError("expected FeatureError")


def test_non_boundary_four_is_not_counted_from_delivery_applied():
    raw = cricsheet_match(
        [
            innings(
                "Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]
            ),
            innings(
                "Beta",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=1),
                            delivery(
                                actual_delivery="0.2", batter_runs=4, non_boundary=True
                            ),
                            delivery(actual_delivery="0.3", batter_runs=0),
                            delivery(actual_delivery="0.4", batter_runs=0),
                        ],
                    )
                ],
                target={"runs": 20, "overs": 2},
            ),
        ],
        dates=["2024-01-01"],
        overs=2,
    )
    match = parse_cricsheet_dict(raw, source_match_id="non-boundary")
    states = MatchStateEngine(match).reconstruct()
    chase = [
        state
        for state in states
        if is_chase_training_state(state) and state.last_delivery
    ]
    after_four = next(
        state
        for state in chase
        if state.last_delivery and state.last_delivery.batter_runs == 4
    )
    assert after_four.last_delivery is not None
    assert after_four.last_delivery.non_boundary is True
    features = extract_feature_vector(after_four, states)
    assert features.values["boundaries_last_6"] == 0.0


def test_source_four_without_non_boundary_flag_counts_as_boundary():
    raw = cricsheet_match(
        [
            innings(
                "Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]
            ),
            innings(
                "Beta",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=1),
                            delivery(actual_delivery="0.2", batter_runs=4),
                            delivery(actual_delivery="0.3", batter_runs=0),
                            delivery(actual_delivery="0.4", batter_runs=0),
                        ],
                    )
                ],
                target={"runs": 20, "overs": 2},
            ),
        ],
        dates=["2024-01-01"],
        overs=2,
    )
    match = parse_cricsheet_dict(raw, source_match_id="true-boundary")
    states = MatchStateEngine(match).reconstruct()
    after_four = next(
        state
        for state in states
        if state.last_delivery is not None and state.last_delivery.batter_runs == 4
    )
    assert after_four.last_delivery is not None
    assert after_four.last_delivery.non_boundary is False
    features = extract_feature_vector(after_four, states, match=match)
    assert features.values["boundaries_last_6"] == 1.0
