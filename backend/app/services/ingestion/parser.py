"""Parse Cricsheet JSON into normalized PulseIQ match records.

The parser copies source fields and applies cricket classification rules.
It does not invent missing statistics, official totals, or player records.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.constants import DEFAULT_BALLS_PER_OVER, KNOWN_EXTRA_TYPES, SOURCE_NAME
from app.core.cricket_rules import counts_as_wicket, is_legal_delivery, overs_notation_to_balls
from app.core.exceptions import ParseError
from app.schemas.match import (
    EventInfo,
    ExtraBreakdown,
    FielderInfo,
    MatchInfo,
    MiscountedOverInfo,
    NormalizedDelivery,
    NormalizedInnings,
    NormalizedMatch,
    NormalizedOver,
    OfficialsInfo,
    OutcomeInfo,
    PenaltyRunsInfo,
    PowerplayInfo,
    ReplacementInfo,
    ReviewInfo,
    SourceProvenance,
    TargetInfo,
    TossInfo,
    WicketInfo,
)


def parse_cricsheet_file(path: str | Path) -> NormalizedMatch:
    file_path = Path(path)
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParseError(f"Unable to read Cricsheet file {file_path}: {exc}") from exc
    return parse_cricsheet_dict(raw, source_path=str(file_path), source_match_id=file_path.stem)


def parse_cricsheet_dict(
    raw: dict[str, Any],
    *,
    source_path: str | None = None,
    source_match_id: str | None = None,
) -> NormalizedMatch:
    if not isinstance(raw, dict):
        raise ParseError("Cricsheet document must be a JSON object")

    meta = _require_object(raw, "meta")
    info = _require_object(raw, "info")
    innings_raw = raw.get("innings")
    if innings_raw is None:
        innings_raw = []
    if not isinstance(innings_raw, list):
        raise ParseError("innings must be an array")

    teams = _require_string_list(info, "teams")
    if len(teams) < 2:
        raise ParseError("info.teams must contain at least two teams")

    provenance = SourceProvenance(
        source=SOURCE_NAME,
        source_match_id=source_match_id or _fallback_match_id(info),
        data_version=_require_str(meta, "data_version"),
        created=_require_str(meta, "created"),
        revision=_require_int(meta, "revision"),
        source_path=source_path,
    )
    match_info = _parse_match_info(info, teams)
    if match_info.balls_per_over <= 0:
        raise ParseError("info.balls_per_over must be a positive integer")
    if match_info.scheduled_overs is not None and match_info.scheduled_overs < 0:
        raise ParseError("info.overs cannot be negative")
    innings = _parse_innings(
        innings_raw,
        teams=teams,
        balls_per_over=match_info.balls_per_over,
    )
    return NormalizedMatch(provenance=provenance, info=match_info, innings=innings)


def _parse_match_info(info: dict[str, Any], teams: tuple[str, ...]) -> MatchInfo:
    toss_raw = _require_object(info, "toss")
    outcome_raw = _require_object(info, "outcome")
    players_raw = info.get("players") or {}
    if not isinstance(players_raw, dict):
        raise ParseError("info.players must be an object")

    players: dict[str, tuple[str, ...]] = {}
    for team, names in players_raw.items():
        if not isinstance(names, list):
            raise ParseError(f"info.players.{team} must be an array")
        players[str(team)] = tuple(str(name) for name in names)

    registry = info.get("registry") or {}
    if registry and not isinstance(registry, dict):
        raise ParseError("info.registry must be an object")
    people = (registry or {}).get("people") or {}
    venues = (registry or {}).get("venues") or {}

    event = None
    if info.get("event"):
        event_raw = _expect_object(info, "event")
        group = event_raw.get("group")
        event = EventInfo(
            name=_optional_str(event_raw.get("name")),
            match_number=_optional_int(event_raw.get("match_number")),
            group=None if group is None else str(group),
            stage=_optional_str(event_raw.get("stage")),
        )

    officials = None
    if info.get("officials"):
        officials_raw = _expect_object(info, "officials")
        officials = OfficialsInfo(
            umpires=_string_tuple(officials_raw.get("umpires")),
            tv_umpires=_string_tuple(officials_raw.get("tv_umpires")),
            reserve_umpires=_string_tuple(officials_raw.get("reserve_umpires")),
            match_referees=_string_tuple(officials_raw.get("match_referees")),
        )

    outcome_by = outcome_raw.get("by") or {}
    if outcome_by and not isinstance(outcome_by, dict):
        raise ParseError("info.outcome.by must be an object")

    missing = info.get("missing") or []
    if missing and not isinstance(missing, list):
        raise ParseError("info.missing must be an array")

    supersubs_raw = info.get("supersubs") or {}
    if supersubs_raw and not isinstance(supersubs_raw, dict):
        raise ParseError("info.supersubs must be an object")

    bowl_out_raw = info.get("bowl_out") or []
    bowl_out: list[dict[str, str]] = []
    if bowl_out_raw:
        if not isinstance(bowl_out_raw, list):
            raise ParseError("info.bowl_out must be an array")
        for entry in bowl_out_raw:
            if isinstance(entry, dict):
                bowl_out.append({str(key): str(value) for key, value in entry.items()})

    return MatchInfo(
        balls_per_over=_optional_int(info.get("balls_per_over")) or DEFAULT_BALLS_PER_OVER,
        match_type=_require_str(info, "match_type"),
        team_type=_optional_str(info.get("team_type")),
        gender=_require_str(info, "gender"),
        scheduled_overs=_optional_int(info.get("overs")),
        season=str(info["season"]) if "season" in info and info["season"] is not None else "",
        dates=_require_string_list(info, "dates"),
        teams=teams,
        venue=_optional_str(info.get("venue")),
        city=_optional_str(info.get("city")),
        event=event,
        toss=TossInfo(
            winner=_require_str(toss_raw, "winner"),
            decision=_require_str(toss_raw, "decision"),
            uncontested=_optional_bool(toss_raw.get("uncontested")),
        ),
        outcome=OutcomeInfo(
            winner=_optional_str(outcome_raw.get("winner")),
            result=_optional_str(outcome_raw.get("result")),
            win_by_runs=_optional_int((outcome_by or {}).get("runs")),
            win_by_wickets=_optional_int((outcome_by or {}).get("wickets")),
            win_by_innings=_optional_int((outcome_by or {}).get("innings")),
            method=_optional_str(outcome_raw.get("method")),
            eliminator=_optional_str(outcome_raw.get("eliminator")),
            bowl_out_winner=_optional_str(outcome_raw.get("bowl_out")),
        ),
        players=players,
        registry_people={str(k): str(v) for k, v in people.items()} if isinstance(people, dict) else {},
        registry_venues={str(k): str(v) for k, v in venues.items()} if isinstance(venues, dict) else {},
        player_of_match=_string_tuple(info.get("player_of_match")),
        officials=officials,
        missing=tuple(missing),
        supersubs={str(k): str(v) for k, v in supersubs_raw.items()} if supersubs_raw else {},
        bowl_out=tuple(bowl_out),
    )


def _parse_innings(
    innings_raw: list[Any],
    *,
    teams: tuple[str, ...],
    balls_per_over: int,
) -> tuple[NormalizedInnings, ...]:
    parsed: list[NormalizedInnings] = []
    sequence = 0
    for index, innings in enumerate(innings_raw, start=1):
        if not isinstance(innings, dict):
            raise ParseError(f"innings[{index}] must be an object")
        batting_team = _require_str(innings, "team")
        if batting_team not in teams:
            raise ParseError(f"innings[{index}] team '{batting_team}' is not in info.teams")
        bowling_team = _other_team(batting_team, teams)
        target = None
        if innings.get("target"):
            target_raw = _expect_object(innings, "target")
            target_runs = _optional_int(target_raw.get("runs"))
            if target_runs is not None and target_runs < 0:
                raise ParseError(f"innings[{index}] target.runs cannot be negative")
            target_overs = target_raw.get("overs")
            if target_overs is not None:
                try:
                    overs_notation_to_balls(target_overs, balls_per_over)
                except ValueError as exc:
                    raise ParseError(f"innings[{index}] has invalid target.overs: {exc}") from exc
            target = TargetInfo(runs=target_runs, overs=target_overs)
        penalty_raw = innings.get("penalty_runs") or {}
        if penalty_raw and not isinstance(penalty_raw, dict):
            raise ParseError(f"innings[{index}].penalty_runs must be an object")
        penalty_pre = _optional_int((penalty_raw or {}).get("pre")) or 0
        penalty_post = _optional_int((penalty_raw or {}).get("post")) or 0
        if penalty_pre < 0 or penalty_post < 0:
            raise ParseError(f"innings[{index}] penalty_runs cannot be negative")

        overs_raw = innings.get("overs")
        if overs_raw is None:
            overs_raw = []
        if not isinstance(overs_raw, list):
            raise ParseError(f"innings[{index}].overs must be an array")

        innings_delivery_number = 0
        overs: list[NormalizedOver] = []
        seen_overs: set[int] = set()
        previous_over_number: int | None = None
        for over in overs_raw:
            if not isinstance(over, dict):
                raise ParseError(f"innings[{index}] contains a non-object over")
            over_number = _require_int(over, "over")
            if over_number < 0:
                raise ParseError(f"innings[{index}] has a negative over number {over_number}")
            if over_number in seen_overs:
                raise ParseError(f"duplicate over {over_number} in innings {index}")
            if previous_over_number is not None and over_number < previous_over_number:
                raise ParseError(
                    f"out-of-order over {over_number} after {previous_over_number} in innings {index}"
                )
            seen_overs.add(over_number)
            previous_over_number = over_number
            deliveries_raw = over.get("deliveries")
            if not isinstance(deliveries_raw, list):
                raise ParseError(f"over {over_number} in innings {index} is missing deliveries")
            if not deliveries_raw:
                raise ParseError(f"over {over_number} in innings {index} has no deliveries")
            deliveries: list[NormalizedDelivery] = []
            for delivery_in_over, delivery_raw in enumerate(deliveries_raw, start=1):
                if not isinstance(delivery_raw, dict):
                    raise ParseError(f"delivery in over {over_number} innings {index} is not an object")
                sequence += 1
                innings_delivery_number += 1
                deliveries.append(
                    _parse_delivery(
                        delivery_raw,
                        sequence=sequence,
                        innings_number=index,
                        innings_delivery_number=innings_delivery_number,
                        over_number=over_number,
                        delivery_in_over=delivery_in_over,
                    )
                )
            overs.append(NormalizedOver(over_number=over_number, deliveries=tuple(deliveries)))

        parsed.append(
            NormalizedInnings(
                innings_number=index,
                batting_team=batting_team,
                bowling_team=bowling_team,
                is_super_over=bool(innings.get("super_over")),
                declared=bool(innings.get("declared")),
                forfeited=bool(innings.get("forfeited")),
                target=target,
                penalty_runs=PenaltyRunsInfo(pre=penalty_pre, post=penalty_post),
                absent_hurt=_string_tuple(innings.get("absent_hurt")),
                powerplays=_parse_powerplays(innings.get("powerplays"), index),
                miscounted_overs=_parse_miscounted(innings.get("miscounted_overs"), index),
                overs=tuple(overs),
            )
        )
    return tuple(parsed)


def _parse_delivery(
    delivery_raw: dict[str, Any],
    *,
    sequence: int,
    innings_number: int,
    innings_delivery_number: int,
    over_number: int,
    delivery_in_over: int,
) -> NormalizedDelivery:
    runs = _require_object(delivery_raw, "runs")
    batter_runs = runs.get("batter", runs.get("batsman"))
    extras_runs = runs.get("extras")
    total_runs = runs.get("total")
    if batter_runs is None or extras_runs is None or total_runs is None:
        raise ParseError(f"delivery {sequence} is missing runs.batter/extras/total")
    batter_runs = _parse_exact_int(batter_runs, f"delivery {sequence} runs.batter")
    extras_runs = _parse_exact_int(extras_runs, f"delivery {sequence} runs.extras")
    total_runs = _parse_exact_int(total_runs, f"delivery {sequence} runs.total")
    if batter_runs < 0 or extras_runs < 0 or total_runs < 0:
        raise ParseError(f"delivery {sequence} has negative run values")
    if batter_runs + extras_runs != total_runs:
        raise ParseError(
            f"delivery {sequence} run components are inconsistent: "
            f"{batter_runs} + {extras_runs} != {total_runs}"
        )

    extras_raw = delivery_raw.get("extras") or {}
    if extras_raw and not isinstance(extras_raw, dict):
        raise ParseError(f"delivery {sequence} extras must be an object")
    extras = _parse_extras(extras_raw, sequence, extras_runs)

    wickets_raw = delivery_raw.get("wickets") or []
    if wickets_raw and not isinstance(wickets_raw, list):
        raise ParseError(f"delivery {sequence} wickets must be an array")
    wickets = tuple(_parse_wicket(wicket, sequence) for wicket in wickets_raw)
    return NormalizedDelivery(
        sequence=sequence,
        innings_number=innings_number,
        innings_delivery_number=innings_delivery_number,
        over_number=over_number,
        delivery_in_over=delivery_in_over,
        actual_delivery=_parse_actual_delivery(
            delivery_raw.get("actual_delivery"),
            over_number=over_number,
            sequence=sequence,
        ),
        batter=_require_str(delivery_raw, "batter"),
        bowler=_require_str(delivery_raw, "bowler"),
        non_striker=_require_str(delivery_raw, "non_striker"),
        batter_runs=batter_runs,
        extras_runs=extras_runs,
        total_runs=total_runs,
        extras=extras,
        is_legal_delivery=is_legal_delivery(extras_raw),
        is_wide=bool(extras_raw.get("wides")),
        is_noball=bool(extras_raw.get("noballs")),
        is_bye=bool(extras_raw.get("byes")),
        is_legbye=bool(extras_raw.get("legbyes")),
        is_penalty=bool(extras_raw.get("penalty")),
        non_boundary=bool(runs.get("non_boundary")),
        wickets=wickets,
        replacements=_parse_replacements(delivery_raw.get("replacements")),
        review=_parse_review(delivery_raw.get("review")),
    )


def _parse_extras(extras_raw: dict[str, Any], sequence: int, extras_runs: int) -> ExtraBreakdown:
    named: dict[str, int] = {}
    for key, value in extras_raw.items():
        if value is None:
            continue
        amount = _parse_exact_int(value, f"delivery {sequence} extra '{key}'")
        if amount < 0:
            raise ParseError(f"delivery {sequence} extra '{key}' cannot be negative")
        if key in KNOWN_EXTRA_TYPES:
            named[key] = amount
    extras = ExtraBreakdown(
        wides=named.get("wides", 0),
        noballs=named.get("noballs", 0),
        byes=named.get("byes", 0),
        legbyes=named.get("legbyes", 0),
        penalty=named.get("penalty", 0),
    )
    if extras.total > extras_runs:
        raise ParseError(
            f"delivery {sequence} named extras {extras.total} exceed runs.extras {extras_runs}"
        )
    return extras


def _parse_wicket(wicket_raw: Any, sequence: int) -> WicketInfo:
    if not isinstance(wicket_raw, dict):
        raise ParseError(f"delivery {sequence} has a non-object wicket")
    kind = _require_str(wicket_raw, "kind")
    fielders: list[FielderInfo] = []
    for fielder in wicket_raw.get("fielders") or []:
        if isinstance(fielder, dict) and fielder.get("name"):
            fielders.append(FielderInfo(name=str(fielder["name"])))
        elif isinstance(fielder, str):
            fielders.append(FielderInfo(name=fielder))
    return WicketInfo(
        kind=kind,
        player_out=_require_str(wicket_raw, "player_out"),
        fielders=tuple(fielders),
        counts_as_wicket=counts_as_wicket(kind),
    )


def _parse_replacements(raw: Any) -> tuple[ReplacementInfo, ...]:
    if not raw:
        return ()
    if not isinstance(raw, dict):
        raise ParseError("replacements must be an object")
    items: list[ReplacementInfo] = []
    for replacement_type in ("match", "role"):
        for entry in raw.get(replacement_type) or []:
            if not isinstance(entry, dict):
                continue
            items.append(
                ReplacementInfo(
                    replacement_type=replacement_type,
                    player_in=_optional_str(entry.get("in")),
                    player_out=_optional_str(entry.get("out")),
                    reason=_optional_str(entry.get("reason")),
                    role=_optional_str(entry.get("role")),
                    team=_optional_str(entry.get("team")),
                )
            )
    return tuple(items)


def _parse_review(raw: Any) -> ReviewInfo | None:
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ParseError("review must be an object")
    umpires_call = raw.get("umpires_call")
    return ReviewInfo(
        team=_require_str(raw, "by"),
        batter=_require_str(raw, "batter"),
        decision=_require_str(raw, "decision"),
        umpire=_optional_str(raw.get("umpire")),
        umpires_call=bool(umpires_call) if umpires_call is not None else None,
    )


def _parse_powerplays(raw: Any, innings_number: int) -> tuple[PowerplayInfo, ...]:
    if not raw:
        return ()
    if not isinstance(raw, list):
        raise ParseError(f"innings[{innings_number}].powerplays must be an array")
    items: list[PowerplayInfo] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        items.append(
            PowerplayInfo(
                type=str(entry.get("type") or ""),
                start=entry.get("from"),
                end=entry.get("to"),
            )
        )
    return tuple(items)


def _parse_miscounted(raw: Any, innings_number: int) -> tuple[MiscountedOverInfo, ...]:
    if not raw:
        return ()
    if not isinstance(raw, dict):
        raise ParseError(f"innings[{innings_number}].miscounted_overs must be an object")
    items: list[MiscountedOverInfo] = []
    for over_number, details in raw.items():
        if not isinstance(details, dict):
            continue
        items.append(
            MiscountedOverInfo(
                over_number=_parse_exact_int(over_number, f"innings[{innings_number}] miscounted over"),
                balls=_parse_exact_int(details.get("balls"), f"innings[{innings_number}] miscounted balls"),
                umpire=_optional_str(details.get("umpire")),
            )
        )
    return tuple(items)


def _other_team(batting_team: str, teams: tuple[str, ...]) -> str:
    for team in teams:
        if team != batting_team:
            return team
    raise ParseError(f"unable to determine bowling team for {batting_team}")


def _fallback_match_id(info: dict[str, Any]) -> str:
    dates = info.get("dates") or ["unknown-date"]
    teams = info.get("teams") or ["unknown", "unknown"]
    return f"{dates[0]}-{teams[0]}-vs-{teams[1]}".replace(" ", "_")


def _require_object(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise ParseError(f"missing or invalid object field '{key}'")
    return value


def _expect_object(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise ParseError(f"field '{key}' must be an object")
    return value


def _require_str(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if value is None or value == "":
        raise ParseError(f"missing required string field '{key}'")
    return str(value)


def _parse_exact_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ParseError(f"{label} must be an integer, got {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ParseError(f"{label} must be an integer, got {value!r}")
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("-") and len(text) > 1 and text[1:].isdigit():
            return int(text)
        if text.isdigit():
            return int(text)
        raise ParseError(f"{label} must be an integer, got {value!r}")
    raise ParseError(f"{label} must be an integer, got {value!r}")


def _parse_actual_delivery(value: Any, *, over_number: int, sequence: int) -> str | None:
    label = _optional_str(value)
    if label is None:
        return None
    if "." not in label:
        return label
    over_text, ball_text = label.split(".", 1)
    if not over_text.isdigit() or not ball_text.isdigit():
        return label
    labeled_over = int(over_text)
    if labeled_over != over_number:
        raise ParseError(
            f"delivery {sequence} actual_delivery {label!r} does not match over {over_number}"
        )
    return label


def _require_int(container: dict[str, Any], key: str) -> int:
    value = container.get(key)
    if value is None:
        raise ParseError(f"missing required integer field '{key}'")
    return _parse_exact_int(value, key)


def _require_string_list(container: dict[str, Any], key: str) -> tuple[str, ...]:
    value = container.get(key)
    if not isinstance(value, list) or not value:
        raise ParseError(f"field '{key}' must be a non-empty array")
    return tuple(str(item) for item in value)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if not isinstance(value, list):
        raise ParseError("expected an array of strings")
    return tuple(str(item) for item in value)


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _optional_int(value: Any, label: str = "value") -> int | None:
    if value is None or value == "":
        return None
    return _parse_exact_int(value, label)


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)
