from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.enums import TargetSource
from app.services.ingestion import parse_cricsheet_file
from app.services.match_engine import MatchStateEngine, validate_match
from app.services.replay import ReplayEngine

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cricsheet"

REAL_MATCHES = {
    "1082591.json": {
        "label": "complete men's IPL",
        "innings": [
            {
                "runs": 207,
                "wickets": 4,
                "legal_balls": 120,
                "deliveries": 125,
                "target": None,
            },
            {
                "runs": 172,
                "wickets": 10,
                "legal_balls": 118,
                "deliveries": 123,
                "target": 208,
            },
        ],
    },
    "1082648.json": {
        "label": "D/L shortened chase",
        "innings": [
            {
                "runs": 128,
                "wickets": 7,
                "legal_balls": 120,
                "deliveries": 122,
                "target": None,
            },
            {
                "runs": 48,
                "wickets": 3,
                "legal_balls": 32,
                "deliveries": 35,
                "target": 48,
                "scheduled_balls": 36,
            },
        ],
    },
    "1359519.json": {
        "label": "no result one innings",
        "innings": [
            {
                "runs": 125,
                "wickets": 7,
                "legal_balls": 116,
                "deliveries": 118,
                "target": None,
            },
        ],
    },
    "1082628.json": {
        "label": "retired hurt",
        "innings": [
            {"runs": 162, "wickets": 8, "wicket_events": 8, "legal_balls": 120},
            {
                "runs": 165,
                "wickets": 5,
                "wicket_events": 6,
                "legal_balls": 119,
                "target": 163,
            },
        ],
    },
    "1304066.json": {
        "label": "retired out",
        "innings": [
            {"runs": 165, "wickets": 6, "wicket_events": 6, "legal_balls": 120},
            {"runs": 162, "wickets": 8, "legal_balls": 120, "target": 166},
        ],
    },
    "335987.json": {
        "label": "miscounted over",
        "innings": [
            {"runs": 166, "wickets": 8, "legal_balls": 119, "deliveries": 122},
            {"runs": 168, "wickets": 4, "legal_balls": 109, "target": 167},
        ],
    },
    "1175358.json": {
        "label": "absent hurt",
        "innings": [
            {"runs": 213, "wickets": 6, "legal_balls": 120},
            {
                "runs": 176,
                "wickets": 9,
                "legal_balls": 116,
                "target": 214,
                "wickets_remaining": 0,
            },
        ],
    },
    "1314906.json": {
        "label": "women's T20",
        "innings": [
            {"runs": 165, "wickets": 7, "legal_balls": 120},
            {"runs": 161, "wickets": 8, "legal_balls": 120, "target": 166},
        ],
    },
    "1082625.json": {
        "label": "super over tie",
        "innings": [
            {"runs": 153, "wickets": 9, "legal_balls": 120, "super_over": False},
            {
                "runs": 153,
                "wickets": 10,
                "legal_balls": 120,
                "target": 154,
                "super_over": False,
            },
            {"runs": 11, "wickets": 2, "legal_balls": 5, "super_over": True},
            {
                "runs": 6,
                "wickets": 0,
                "legal_balls": 6,
                "super_over": True,
                "derived_target": 12,
            },
        ],
    },
    "1216517.json": {
        "label": "double super over",
        "innings": [
            {"runs": 176, "super_over": False},
            {"runs": 176, "super_over": False, "target": 177},
            {"runs": 5, "super_over": True},
            {"runs": 5, "super_over": True, "derived_target": 6},
            {"runs": 11, "super_over": True},
            {"runs": 15, "super_over": True, "derived_target": 12},
        ],
    },
}


def _available_matches() -> list[str]:
    return [name for name in REAL_MATCHES if (FIXTURE_DIR / name).exists()]


@pytest.mark.parametrize("filename", _available_matches())
def test_real_match_validates_against_source(filename: str):
    path = FIXTURE_DIR / filename
    raw = json.loads(path.read_text(encoding="utf-8"))
    match = parse_cricsheet_file(path)
    report = validate_match(match, raw=raw)
    assert report.ok, report.errors
    engine_states = MatchStateEngine(match).reconstruct()
    replay_states = ReplayEngine(match).play_all()
    assert [state.model_dump() for state in engine_states] == [
        state.model_dump() for state in replay_states
    ]


@pytest.mark.parametrize("filename", _available_matches())
def test_real_match_reconstructed_totals(filename: str):
    match = parse_cricsheet_file(FIXTURE_DIR / filename)
    states = MatchStateEngine(match).reconstruct()
    expected_list = REAL_MATCHES[filename]["innings"]
    assert len(match.innings) == len(expected_list)
    for innings, expected in zip(match.innings, expected_list, strict=True):
        final = [
            state
            for state in states
            if state.innings_number == innings.innings_number
            and state.innings_just_completed
        ][-1]
        assert final.innings_runs == expected["runs"]
        if "wickets" in expected:
            assert final.innings_wickets == expected["wickets"]
        if "wicket_events" in expected:
            assert final.innings_wicket_events == expected["wicket_events"]
        if "legal_balls" in expected:
            assert final.legal_balls == expected["legal_balls"]
        if "deliveries" in expected:
            assert final.total_deliveries == expected["deliveries"]
        if expected.get("target") is not None:
            assert final.target == expected["target"]
            assert final.target_source == TargetSource.CRICSHEET
        if expected.get("scheduled_balls") is not None:
            assert final.scheduled_balls == expected["scheduled_balls"]
        if expected.get("wickets_remaining") is not None:
            assert final.wickets_remaining == expected["wickets_remaining"]
        if "super_over" in expected:
            assert final.is_super_over is expected["super_over"]
        if expected.get("derived_target") is not None:
            assert final.target == expected["derived_target"]
            assert final.target_source == TargetSource.DERIVED_PREVIOUS_INNINGS


def test_penalty_extra_is_legal_and_included_in_total():
    path = FIXTURE_DIR / "335988.json"
    if not path.exists():
        pytest.skip("penalty extras fixture not copied")
    match = parse_cricsheet_file(path)
    penalty = [delivery for delivery in match.deliveries if delivery.is_penalty]
    assert penalty
    assert all(item.is_legal_delivery for item in penalty)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert validate_match(match, raw=raw).ok
