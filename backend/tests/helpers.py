"""Builders for compact synthetic Cricsheet documents."""

from __future__ import annotations

from typing import Any


def delivery(
    *,
    actual_delivery: str,
    batter: str = "A Batter",
    bowler: str = "B Bowler",
    non_striker: str = "C Partner",
    batter_runs: int = 0,
    extras_runs: int = 0,
    extras: dict[str, int] | None = None,
    wickets: list[dict[str, Any]] | None = None,
    non_boundary: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "actual_delivery": actual_delivery,
        "batter": batter,
        "bowler": bowler,
        "non_striker": non_striker,
        "runs": {
            "batter": batter_runs,
            "extras": extras_runs,
            "total": batter_runs + extras_runs,
        },
    }
    if extras:
        payload["extras"] = extras
    if wickets:
        payload["wickets"] = wickets
    if non_boundary:
        payload["runs"]["non_boundary"] = True
    return payload


def over(over_number: int, deliveries: list[dict[str, Any]]) -> dict[str, Any]:
    return {"over": over_number, "deliveries": deliveries}


def innings(
    team: str,
    overs: list[dict[str, Any]],
    *,
    target: dict[str, Any] | None = None,
    super_over: bool = False,
    absent_hurt: list[str] | None = None,
    penalty_runs: dict[str, int] | None = None,
    forfeited: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"team": team, "overs": overs}
    if target:
        payload["target"] = target
    if super_over:
        payload["super_over"] = True
    if absent_hurt:
        payload["absent_hurt"] = absent_hurt
    if penalty_runs:
        payload["penalty_runs"] = penalty_runs
    if forfeited:
        payload["forfeited"] = True
    return payload


def cricsheet_match(
    innings_list: list[dict[str, Any]],
    *,
    teams: tuple[str, str] = ("Alpha", "Beta"),
    outcome: dict[str, Any] | None = None,
    overs: int = 20,
    balls_per_over: int = 6,
    match_type: str = "T20",
    season: str | int = "2024",
    dates: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "meta": {"data_version": "1.2.0", "created": "2024-01-01", "revision": 1},
        "info": {
            "balls_per_over": balls_per_over,
            "match_type": match_type,
            "team_type": "club",
            "gender": "male",
            "overs": overs,
            "season": season,
            "dates": dates or ["2024-01-01"],
            "teams": list(teams),
            "venue": "Test Ground",
            "city": "Test City",
            "players": {
                teams[0]: [f"{teams[0][0]}{index}" for index in range(11)],
                teams[1]: [f"{teams[1][0]}{index}" for index in range(11)],
            },
            "registry": {"people": {}, "venues": {}},
            "toss": {"winner": teams[0], "decision": "bat"},
            "outcome": outcome
            or {
                "winner": teams[0],
                "by": {"runs": 1},
            },
        },
        "innings": innings_list,
    }
