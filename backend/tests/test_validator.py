import json

from app.services.ingestion import parse_cricsheet_dict
from app.services.match_engine import validate_match
from tests.helpers import cricsheet_match, delivery, innings, over


def test_validator_accepts_consistent_source_totals():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=4),
                            delivery(actual_delivery="0.2", extras_runs=1, extras={"wides": 1}),
                            delivery(
                                actual_delivery="0.2",
                                wickets=[{"kind": "bowled", "player_out": "A Batter"}],
                            ),
                        ],
                    )
                ],
            )
        ]
    )
    match = parse_cricsheet_dict(raw, source_match_id="valid")
    report = validate_match(match, raw=raw)
    assert report.ok is True
    assert report.innings[0].source_runs == 5
    assert report.innings[0].reconstructed_runs == 5
    assert report.innings[0].source_legal_balls == 2
    assert report.innings[0].reconstructed_legal_balls == 2


def test_validator_detects_raw_total_mismatch():
    raw = cricsheet_match(
        [innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])])]
    )
    match = parse_cricsheet_dict(raw, source_match_id="tampered")
    tampered = json.loads(json.dumps(raw))
    tampered["innings"][0]["overs"][0]["deliveries"][0]["runs"]["total"] = 99
    report = validate_match(match, raw=tampered)
    assert report.ok is False
    assert any(issue.code == "runs_mismatch" for issue in report.errors)


def test_validator_flags_internal_run_component_errors():
    raw = cricsheet_match(
        [innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])])]
    )
    match = parse_cricsheet_dict(raw, source_match_id="components")
    broken = match.model_copy(
        update={
            "innings": (
                match.innings[0].model_copy(
                    update={
                        "overs": (
                            match.innings[0].overs[0].model_copy(
                                update={
                                    "deliveries": (
                                        match.deliveries[0].model_copy(
                                            update={"total_runs": 9},
                                        ),
                                    )
                                }
                            ),
                        )
                    }
                ),
            )
        }
    )
    report = validate_match(broken, raw=raw)
    assert report.ok is False
    assert {issue.code for issue in report.errors} >= {"runs_components_mismatch", "runs_mismatch"}
