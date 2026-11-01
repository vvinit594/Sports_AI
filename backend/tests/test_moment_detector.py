import pytest

from app.core.exceptions import IntelligenceError
from app.services.intelligence.moment_detector import (
    MomentDetectorConfig,
    MomentType,
    detect_significant_moments,
)
from app.services.ml.features import is_chase_training_state
from app.services.ml.inference import ProbabilityPrediction
from tests.ml_helpers import two_innings_chase


def _predictions(states, values: list[float]) -> list[ProbabilityPrediction]:
    chase = [state for state in states if is_chase_training_state(state)]
    selected = chase[: len(values)]
    if len(selected) != len(values):
        raise AssertionError(f"need {len(values)} chase states, got {len(selected)}")
    return [
        ProbabilityPrediction(
            source_match_id=state.source_match_id,
            sequence=state.sequence,
            probability=value,
            model_id="test",
        )
        for state, value in zip(selected, values, strict=True)
    ]


def test_probability_swing_above_threshold_is_detected():
    _, states = two_innings_chase(
        match_id="moment-swing",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 1],
        winner="Beta",
    )
    chase = [state for state in states if is_chase_training_state(state)]
    predictions = _predictions(states, [0.40, 0.55, 0.56, 0.57][: len(chase)])
    moments = detect_significant_moments(
        states,
        predictions,
        config=MomentDetectorConfig(
            probability_swing_threshold=0.08,
            major_boundary_runs=10,
            chase_equation_rrr_delta=100,
            cooldown_deliveries=1,
        ),
    )
    assert moments
    assert moments[0].moment_type == MomentType.WIN_PROBABILITY_SWING
    assert moments[0].probability_change == pytest.approx(0.15)
    assert moments[0].probability_before == pytest.approx(0.40)
    assert moments[0].probability_after == pytest.approx(0.55)


def test_below_threshold_swings_are_ignored():
    _, states = two_innings_chase(
        match_id="moment-quiet",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 1],
        winner="Beta",
    )
    chase = [state for state in states if is_chase_training_state(state)]
    predictions = _predictions(states, [0.50, 0.52, 0.53, 0.54][: len(chase)])
    moments = detect_significant_moments(
        states,
        predictions,
        config=MomentDetectorConfig(
            probability_swing_threshold=0.08,
            major_boundary_runs=10,
            chase_equation_rrr_delta=100,
            cooldown_deliveries=1,
        ),
    )
    assert moments == []


def test_cooldown_and_duplicate_suppression():
    _, states = two_innings_chase(
        match_id="moment-cool",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 1, 1, 1],
        winner="Beta",
    )
    chase = [state for state in states if is_chase_training_state(state)]
    values = [0.20, 0.40, 0.70, 0.90, 0.10, 0.80][: len(chase)]
    predictions = _predictions(states, values)
    moments = detect_significant_moments(
        states,
        predictions,
        config=MomentDetectorConfig(
            probability_swing_threshold=0.08,
            major_boundary_runs=10,
            chase_equation_rrr_delta=100,
            cooldown_deliveries=6,
        ),
    )
    assert len(moments) == 1
    duplicated_states = list(states) + [chase[1]]
    duplicated_predictions = predictions + [predictions[1]]
    again = detect_significant_moments(
        duplicated_states,
        duplicated_predictions,
        config=MomentDetectorConfig(
            probability_swing_threshold=0.08,
            major_boundary_runs=10,
            chase_equation_rrr_delta=100,
            cooldown_deliveries=6,
        ),
    )
    assert len(again) == 1
    assert again[0].sequence == moments[0].sequence


def test_high_pressure_wicket_is_detected():
    from app.services.ingestion import parse_cricsheet_dict
    from app.services.match_engine import MatchStateEngine
    from tests.helpers import cricsheet_match, delivery, innings, over

    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery=f"0.{index + 1}", batter_runs=1)
                            for index in range(6)
                        ],
                    )
                ],
            ),
            innings(
                "Beta",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=1),
                            delivery(
                                actual_delivery="0.2",
                                batter_runs=0,
                                wickets=[{"kind": "bowled", "player_out": "A Batter"}],
                            ),
                            delivery(actual_delivery="0.3", batter_runs=0),
                            delivery(actual_delivery="0.4", batter_runs=0),
                        ],
                    )
                ],
                target={"runs": 40, "overs": 2},
            ),
        ],
        overs=2,
        dates=["2024-01-01"],
    )
    match = parse_cricsheet_dict(raw, source_match_id="moment-wicket")
    states = MatchStateEngine(match).reconstruct()
    chase = [
        state
        for state in states
        if is_chase_training_state(state) and state.last_delivery is not None
    ]
    predictions = [
        ProbabilityPrediction(
            source_match_id=match.source_match_id,
            sequence=chase[0].sequence,
            probability=0.45,
            model_id="test",
        ),
        ProbabilityPrediction(
            source_match_id=match.source_match_id,
            sequence=chase[1].sequence,
            probability=0.30,
            model_id="test",
        ),
    ]
    moments = detect_significant_moments(
        states,
        predictions,
        config=MomentDetectorConfig(
            probability_swing_threshold=0.50,
            major_boundary_runs=10,
            chase_equation_rrr_delta=100,
            high_pressure_required_run_rate=10.0,
            high_pressure_balls_remaining=36,
            cooldown_deliveries=1,
        ),
    )
    assert moments
    assert moments[0].moment_type == MomentType.HIGH_PRESSURE_WICKET
    assert any("wicket" in reason for reason in moments[0].reasons)


def _quiet_config(**overrides) -> MomentDetectorConfig:
    values = {
        "probability_swing_threshold": 0.08,
        "major_boundary_runs": 10,
        "chase_equation_rrr_delta": 100,
        "cooldown_deliveries": 1,
    }
    values.update(overrides)
    return MomentDetectorConfig(**values)


def test_identical_duplicate_predictions_are_deduplicated():
    _, states = two_innings_chase(
        match_id="moment-dup-ok",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 1],
        winner="Beta",
    )
    chase = [state for state in states if is_chase_training_state(state)]
    predictions = _predictions(states, [0.40, 0.55, 0.56, 0.57][: len(chase)])
    moments = detect_significant_moments(
        states,
        predictions + predictions,
        config=_quiet_config(),
    )
    assert moments
    assert moments[0].probability_change == pytest.approx(0.15)


def test_conflicting_duplicate_predictions_are_rejected():
    _, states = two_innings_chase(
        match_id="moment-dup-bad",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 0, 0],
        winner="Beta",
    )
    predictions = _predictions(states, [0.40, 0.55])
    conflict = predictions[0].model_copy(update={"probability": 0.99})
    with pytest.raises(IntelligenceError, match="conflicting predictions"):
        detect_significant_moments(states, [predictions[0], conflict, predictions[1]])


def test_mixed_match_ids_are_rejected():
    _, states_a = two_innings_chase(
        match_id="moment-a",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 0, 0],
        winner="Beta",
    )
    _, states_b = two_innings_chase(
        match_id="moment-b",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 0, 0],
        winner="Beta",
    )
    predictions = _predictions(states_a, [0.40, 0.55]) + _predictions(states_b, [0.10, 0.90])
    with pytest.raises(IntelligenceError, match="same source_match_id"):
        detect_significant_moments(states_a, predictions)


def test_states_from_another_match_are_rejected():
    _, states_a = two_innings_chase(
        match_id="moment-state-a",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 0, 0],
        winner="Beta",
    )
    _, states_b = two_innings_chase(
        match_id="moment-state-b",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 0, 0],
        winner="Beta",
    )
    predictions = _predictions(states_a, [0.40, 0.55])
    with pytest.raises(IntelligenceError, match="do not match"):
        detect_significant_moments(list(states_a) + list(states_b), predictions)


def test_prediction_without_matching_state_is_rejected():
    _, states = two_innings_chase(
        match_id="moment-missing-state",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 0, 0],
        winner="Beta",
    )
    predictions = _predictions(states, [0.40, 0.55])
    orphan = predictions[0].model_copy(update={"sequence": 99_999})
    with pytest.raises(IntelligenceError, match="no matching state"):
        detect_significant_moments(states, predictions + [orphan])


def test_input_order_does_not_change_detected_moments():
    _, states = two_innings_chase(
        match_id="moment-order",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 1],
        winner="Beta",
    )
    chase = [state for state in states if is_chase_training_state(state)]
    predictions = _predictions(states, [0.40, 0.55, 0.56, 0.57][: len(chase)])
    config = _quiet_config()
    forward = detect_significant_moments(states, predictions, config=config)
    reversed_moments = detect_significant_moments(
        list(reversed(states)),
        list(reversed(predictions)),
        config=config,
    )
    assert [moment.sequence for moment in forward] == [
        moment.sequence for moment in reversed_moments
    ]
    assert [moment.probability_change for moment in forward] == [
        moment.probability_change for moment in reversed_moments
    ]


def test_cooldown_uses_delivery_sequence_numbers():
    _, states = two_innings_chase(
        match_id="moment-seq-cool",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 1, 1, 1],
        winner="Beta",
    )
    chase = [state for state in states if is_chase_training_state(state) and state.last_delivery]
    first, second, last = chase[0], chase[1], chase[-1]
    gap = last.sequence - second.sequence
    assert gap >= 2
    predictions = [
        ProbabilityPrediction(
            source_match_id=state.source_match_id,
            sequence=state.sequence,
            probability=value,
            model_id="test",
        )
        for state, value in (
            (first, 0.20),
            (second, 0.50),
            (last, 0.90),
        )
    ]
    moments = detect_significant_moments(
        states,
        predictions,
        config=_quiet_config(cooldown_deliveries=gap + 1),
    )
    assert [moment.sequence for moment in moments] == [second.sequence]
    resumed = detect_significant_moments(
        states,
        predictions,
        config=_quiet_config(cooldown_deliveries=gap),
    )
    assert [moment.sequence for moment in resumed] == [second.sequence, last.sequence]
