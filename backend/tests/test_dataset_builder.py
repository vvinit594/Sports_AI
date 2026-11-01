from app.services.ingestion import parse_cricsheet_dict
from app.services.ml.dataset_builder import (
    audit_matches,
    build_training_dataset,
    chase_win_label,
    chronological_match_split,
    exclusion_category,
)
from app.services.ml.features import is_chase_training_state
from tests.helpers import cricsheet_match, delivery, innings, over
from tests.ml_helpers import two_innings_chase


def test_chase_win_and_loss_labels():
    won, _ = two_innings_chase(
        match_id="label-win",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 4],
        winner="Beta",
    )
    lost, _ = two_innings_chase(
        match_id="label-loss",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[0] * 12,
        winner="Alpha",
        outcome={"winner": "Alpha", "by": {"runs": 6}},
    )
    assert chase_win_label(won) == (1, None)
    assert chase_win_label(lost) == (0, None)


def test_invalid_outcomes_are_excluded():
    cases = [
        ({"result": "no result"}, "no_result"),
        ({"result": "tie", "eliminator": "Alpha"}, "tie"),
        ({"winner": "Beta", "method": "D/L", "by": {"wickets": 3}}, "method:D/L"),
        ({"winner": "Beta", "by": {"wickets": 2}}, "super_over_present"),
    ]
    first = innings(
        "Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]
    )
    chase = innings(
        "Beta",
        [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
        target={"runs": 10, "overs": 2},
    )
    super_over = innings(
        "Alpha",
        [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
        super_over=True,
    )
    for outcome, expected in cases:
        innings_list = [first, chase]
        if expected == "super_over_present":
            innings_list.append(super_over)
        match = parse_cricsheet_dict(
            cricsheet_match(
                innings_list, outcome=outcome, overs=2, dates=["2024-01-01"]
            ),
            source_match_id=expected,
        )
        assert chase_win_label(match) == (None, expected)


def test_terminal_states_excluded_from_training_examples():
    match, states = two_innings_chase(
        match_id="ds-terminal",
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 4],
        winner="Beta",
    )
    dataset = build_training_dataset([match])
    sequences = {example.sequence for example in dataset.examples}
    for state in states:
        if not is_chase_training_state(state):
            assert state.sequence not in sequences


def test_match_level_split_has_no_delivery_leakage():
    matches = []
    for index, (date, winner) in enumerate(
        [
            ("2020-01-01", "Beta"),
            ("2020-01-02", "Alpha"),
            ("2020-01-03", "Beta"),
            ("2020-01-04", "Alpha"),
        ]
    ):
        match, _ = two_innings_chase(
            match_id=f"split-{index}",
            date=date,
            first_innings_runs=[1, 1, 1, 1, 1, 1],
            chase_runs=[1, 1, 1, 4] if winner == "Beta" else [0] * 12,
            winner=winner,
            outcome={
                "winner": winner,
                "by": {"wickets": 3} if winner == "Beta" else {"runs": 6},
            },
        )
        matches.append(match)

    dataset = build_training_dataset(matches)
    assert dataset.train_match_ids == ("split-0", "split-1")
    assert dataset.validation_match_ids == ("split-2",)
    assert dataset.test_match_ids == ("split-3",)
    by_split: dict[str, set[str]] = {"train": set(), "validation": set(), "test": set()}
    for example in dataset.examples:
        by_split[example.split].add(example.source_match_id)
    assert by_split["train"].isdisjoint(by_split["validation"])
    assert by_split["train"].isdisjoint(by_split["test"])
    assert by_split["validation"].isdisjoint(by_split["test"])
    assert dataset.evaluation_is_meaningful is False


def test_chronological_split_keeps_matches_together():
    split = chronological_match_split(
        [
            ("late", "2022-01-01"),
            ("early", "2020-01-01"),
            ("mid", "2021-01-01"),
            ("latest", "2023-01-01"),
        ]
    )
    assert split["train"] == ("early", "mid")
    assert split["validation"] == ("late",)
    assert split["test"] == ("latest",)


def test_no_result_match_adds_zero_examples():
    raw = cricsheet_match(
        [innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])])],
        outcome={"result": "no result"},
        dates=["2024-01-01"],
    )
    match = parse_cricsheet_dict(raw, source_match_id="no-result")
    dataset = build_training_dataset([match])
    assert dataset.examples == ()
    assert dataset.audit.abandoned_or_no_result == 1


def _minimal_chase(
    outcome, *, match_id: str, match_type: str = "T20", extra_innings=None
):
    innings_list = [
        innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]),
        innings(
            "Beta",
            [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
            target={"runs": 10, "overs": 2},
        ),
    ]
    if extra_innings:
        innings_list.extend(extra_innings)
    raw = cricsheet_match(
        innings_list,
        outcome=outcome,
        overs=2,
        dates=["2024-01-01"],
        match_type=match_type,
    )
    return parse_cricsheet_dict(raw, source_match_id=match_id)


def test_audit_categories_are_mutually_exclusive():
    first_only = parse_cricsheet_dict(
        cricsheet_match(
            [
                innings(
                    "Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]
                )
            ],
            outcome={"winner": "Alpha", "by": {"runs": 1}},
            overs=2,
            dates=["2024-01-01"],
        ),
        source_match_id="no-chase",
    )
    no_target = parse_cricsheet_dict(
        cricsheet_match(
            [
                innings(
                    "Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]
                ),
                innings(
                    "Beta", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])]
                ),
            ],
            outcome={"winner": "Beta", "by": {"wickets": 2}},
            overs=2,
            dates=["2024-01-01"],
        ),
        source_match_id="no-target",
    )
    matches = [
        _minimal_chase({"result": "no result"}, match_id="nr"),
        _minimal_chase({"result": "tie", "eliminator": "Alpha"}, match_id="tie"),
        _minimal_chase(
            {"winner": "Beta", "method": "D/L", "by": {"wickets": 1}}, match_id="dl"
        ),
        _minimal_chase(
            {"winner": "Beta", "by": {"wickets": 1}},
            match_id="so",
            extra_innings=[
                innings(
                    "Alpha",
                    [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
                    super_over=True,
                )
            ],
        ),
        _minimal_chase({"winner": "Gamma", "by": {"runs": 1}}, match_id="bad-winner"),
        _minimal_chase({"result": "draw"}, match_id="draw"),
        _minimal_chase(
            {"winner": "Beta", "by": {"wickets": 1}}, match_id="odi", match_type="ODI"
        ),
        first_only,
        no_target,
    ]
    audit = audit_matches(matches)
    buckets = [
        audit.unsupported_match_formats,
        audit.abandoned_or_no_result,
        audit.tied_matches,
        audit.dls_or_method_matches,
        audit.super_over_or_eliminator_matches,
        audit.missing_or_invalid_binary_outcomes,
        audit.incomplete_or_unsupported,
    ]
    assert audit.completed_usable_matches == 0
    assert sum(buckets) == audit.total_matches == 9
    assert audit.unsupported_match_formats == 1
    assert audit.abandoned_or_no_result == 1
    assert audit.tied_matches == 1
    assert audit.dls_or_method_matches == 1
    assert audit.super_over_or_eliminator_matches == 1
    assert audit.missing_or_invalid_binary_outcomes == 3
    assert audit.incomplete_or_unsupported == 1
    assert exclusion_category("unsupported_match_type") == "unsupported_match_formats"
    assert exclusion_category("tie") != exclusion_category("super_over_present")
