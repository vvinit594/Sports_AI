"""Synthetic T20 matches for Phase 2 feature, dataset, and inference tests."""

from __future__ import annotations

from typing import Any

from app.services.ingestion import parse_cricsheet_dict
from app.services.match_engine import MatchStateEngine
from tests.helpers import cricsheet_match, delivery, innings, over


def legal_over(over_number: int, runs: list[int]) -> dict[str, Any]:
    balls = [
        delivery(actual_delivery=f"{over_number}.{index + 1}", batter_runs=run)
        for index, run in enumerate(runs)
    ]
    return over(over_number, balls)


def two_innings_chase(
    *,
    match_id: str,
    date: str,
    first_innings_runs: list[int],
    chase_runs: list[int],
    winner: str,
    outcome: dict[str, Any] | None = None,
    teams: tuple[str, str] = ("Alpha", "Beta"),
    overs: int = 2,
) -> tuple[Any, list]:
    first_overs = _overs_from_runs(first_innings_runs)
    chase_overs = _overs_from_runs(chase_runs)
    target = sum(first_innings_runs) + 1
    raw = cricsheet_match(
        [
            innings(teams[0], first_overs),
            innings(teams[1], chase_overs, target={"runs": target, "overs": overs}),
        ],
        teams=teams,
        outcome=outcome or {"winner": winner, "by": {"wickets": 4}},
        overs=overs,
        dates=[date],
    )
    match = parse_cricsheet_dict(raw, source_match_id=match_id)
    return match, MatchStateEngine(match).reconstruct()


def _overs_from_runs(runs: list[int]) -> list[dict[str, Any]]:
    grouped: list[list[int]] = []
    current: list[int] = []
    for run in runs:
        current.append(run)
        if len(current) == 6:
            grouped.append(current)
            current = []
    if current:
        grouped.append(current)
    return [legal_over(index, chunk) for index, chunk in enumerate(grouped)]
