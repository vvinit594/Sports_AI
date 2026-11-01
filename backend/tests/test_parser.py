import pytest

from app.core.exceptions import ParseError
from app.services.ingestion import parse_cricsheet_dict
from tests.helpers import cricsheet_match, delivery, innings, over


def test_parser_normalizes_legal_and_illegal_deliveries():
    raw = cricsheet_match(
        [
            innings(
                "Alpha",
                [
                    over(
                        0,
                        [
                            delivery(actual_delivery="0.1", batter_runs=1),
                            delivery(
                                actual_delivery="0.2",
                                extras_runs=1,
                                extras={"wides": 1},
                            ),
                            delivery(
                                actual_delivery="0.2",
                                extras_runs=1,
                                extras={"noballs": 1},
                            ),
                            delivery(
                                actual_delivery="0.2",
                                extras_runs=1,
                                extras={"byes": 1},
                            ),
                            delivery(
                                actual_delivery="0.3",
                                extras_runs=2,
                                extras={"legbyes": 2},
                            ),
                        ],
                    )
                ],
            )
        ]
    )
    match = parse_cricsheet_dict(raw, source_match_id="synthetic-extras")
    deliveries = match.deliveries
    assert [item.is_legal_delivery for item in deliveries] == [True, False, False, True, True]
    assert deliveries[1].is_wide is True
    assert deliveries[2].is_noball is True
    assert deliveries[3].is_bye is True
    assert deliveries[4].is_legbye is True
    assert match.info.season == "2024"


def test_season_integer_is_coerced_to_string():
    raw = cricsheet_match([innings("Alpha", [over(0, [delivery(actual_delivery="0.1")])])], season=2017)
    match = parse_cricsheet_dict(raw, source_match_id="season-int")
    assert match.info.season == "2017"


def test_wickets_preserve_kind_and_counting_flag():
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
                            ),
                            delivery(
                                actual_delivery="0.2",
                                batter_runs=1,
                                wickets=[{"kind": "retired hurt", "player_out": "A Batter"}],
                            ),
                            delivery(
                                actual_delivery="0.3",
                                extras_runs=1,
                                extras={"wides": 1},
                                wickets=[{"kind": "stumped", "player_out": "A Batter"}],
                            ),
                        ],
                    )
                ],
            )
        ]
    )
    match = parse_cricsheet_dict(raw, source_match_id="wickets")
    kinds = [(item.wickets[0].kind, item.wickets[0].counts_as_wicket, item.is_legal_delivery) for item in match.deliveries]
    assert kinds == [
        ("bowled", True, True),
        ("retired hurt", False, True),
        ("stumped", True, False),
    ]


def test_super_over_and_target_are_preserved_not_invented():
    raw = cricsheet_match(
        [
            innings("Alpha", [over(0, [delivery(actual_delivery="0.1", batter_runs=4)])]),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=1)])],
                target={"overs": 20, "runs": 5},
            ),
            innings(
                "Beta",
                [over(0, [delivery(actual_delivery="0.1", batter_runs=2)])],
                super_over=True,
            ),
        ]
    )
    match = parse_cricsheet_dict(raw, source_match_id="so")
    assert match.innings[0].target is None
    assert match.innings[1].target is not None
    assert match.innings[1].target.runs == 5
    assert match.innings[2].is_super_over is True
    assert match.innings[2].target is None


def test_missing_required_fields_raise():
    with pytest.raises(ParseError):
        parse_cricsheet_dict({"meta": {}, "info": {}}, source_match_id="bad")


def test_parser_does_not_require_supersubs():
    raw = cricsheet_match([innings("Alpha", [over(0, [delivery(actual_delivery="0.1")])])])
    raw["info"].pop("supersubs", None)
    match = parse_cricsheet_dict(raw, source_match_id="no-supersub")
    assert match.info.supersubs == {}
