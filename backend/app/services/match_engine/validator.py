"""Validate reconstructed match totals against Cricsheet source records."""

from __future__ import annotations

from typing import Any

from app.core.cricket_rules import counts_as_wicket, is_legal_delivery
from app.schemas.enums import KnowledgeHorizon
from app.schemas.match import NormalizedInnings, NormalizedMatch
from app.schemas.validation import InningsValidation, Issue, ValidationReport
from app.services.match_engine.engine import MatchStateEngine


def validate_match(
    match: NormalizedMatch,
    raw: dict[str, Any] | None = None,
) -> ValidationReport:
    """Compare reconstructed innings totals with source delivery sums.

    When `raw` is provided, source totals are taken only from the original
    Cricsheet JSON. Parser-derived values are not used as a stand-in.
    """

    engine = MatchStateEngine(match)
    states = engine.reconstruct()
    errors: list[Issue] = []
    warnings: list[Issue] = []
    innings_reports: list[InningsValidation] = []

    raw_innings: list[Any] | None = None
    if raw is not None:
        raw_innings = raw.get("innings")
        if not isinstance(raw_innings, list):
            errors.append(Issue(code="raw_innings_missing", message="raw document has no innings array"))
            raw_innings = []
        elif len(raw_innings) != len(match.innings):
            errors.append(
                Issue(
                    code="innings_count_mismatch",
                    message=(
                        f"raw innings count {len(raw_innings)} does not match "
                        f"parsed innings count {len(match.innings)}"
                    ),
                )
            )
        _check_raw_sequence(raw_innings, match, errors, warnings)

    for innings in match.innings:
        source = _source_innings_totals(innings, raw_innings, errors)
        reconstructed = _reconstructed_innings_totals(innings, states)
        report = InningsValidation(
            innings_number=innings.innings_number,
            batting_team=innings.batting_team,
            is_super_over=innings.is_super_over,
            source_runs=source["runs"],
            reconstructed_runs=reconstructed["runs"],
            source_wicket_events=source["wicket_events"],
            reconstructed_wicket_events=reconstructed["wicket_events"],
            source_counting_wickets=source["wickets"],
            reconstructed_wickets=reconstructed["wickets"],
            source_legal_balls=source["legal_balls"],
            reconstructed_legal_balls=reconstructed["legal_balls"],
            source_deliveries=source["deliveries"],
            reconstructed_deliveries=reconstructed["deliveries"],
            source_target_runs=source["target_runs"],
            reconstructed_target_runs=reconstructed["target_runs"],
        )
        innings_reports.append(report)
        _compare_counts(report, errors)
        _check_normalized_delivery_consistency(innings, errors)

        if innings.batting_team not in match.info.teams:
            errors.append(
                Issue(
                    code="unknown_batting_team",
                    message=f"{innings.batting_team} is not listed in info.teams",
                    innings_number=innings.innings_number,
                )
            )

    _add_outcome_warnings(match, innings_reports, warnings)

    return ValidationReport(
        source_match_id=match.source_match_id,
        ok=not errors,
        innings=tuple(innings_reports),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _check_raw_sequence(
    raw_innings: list[Any],
    match: NormalizedMatch,
    errors: list[Issue],
    warnings: list[Issue],
) -> None:
    seen_super_over = False
    previous_regulation_team: str | None = None
    for index, raw in enumerate(raw_innings, start=1):
        if not isinstance(raw, dict):
            errors.append(
                Issue(
                    code="raw_innings_not_object",
                    message=f"raw innings[{index}] is not an object",
                    innings_number=index,
                )
            )
            continue
        is_super_over = bool(raw.get("super_over"))
        team = raw.get("team")
        if seen_super_over and not is_super_over:
            errors.append(
                Issue(
                    code="super_over_before_regulation",
                    message="a regulation innings appears after a super over",
                    innings_number=index,
                )
            )
        if is_super_over:
            seen_super_over = True
        elif previous_regulation_team is not None and team == previous_regulation_team:
            warnings.append(
                Issue(
                    code="regulation_same_batting_team",
                    message="consecutive regulation innings have the same batting team",
                    innings_number=index,
                )
            )
        if not is_super_over and team is not None:
            previous_regulation_team = str(team)

        if index <= len(match.innings):
            parsed = match.innings[index - 1]
            if team is not None and str(team) != parsed.batting_team:
                errors.append(
                    Issue(
                        code="innings_team_mismatch",
                        message=(
                            f"raw batting team '{team}' does not match "
                            f"parsed team '{parsed.batting_team}'"
                        ),
                        innings_number=index,
                    )
                )
            if is_super_over != parsed.is_super_over:
                errors.append(
                    Issue(
                        code="super_over_flag_mismatch",
                        message="raw super_over flag does not match the parsed innings",
                        innings_number=index,
                    )
                )
            raw_target = (raw.get("target") or {}).get("runs") if isinstance(raw.get("target"), dict) else None
            parsed_target = parsed.target.runs if parsed.target else None
            if raw_target is not None and parsed_target is not None and int(raw_target) != parsed_target:
                errors.append(
                    Issue(
                        code="target_mismatch",
                        message=f"target mismatch: source={raw_target} reconstructed={parsed_target}",
                        innings_number=index,
                    )
                )
            if index == 1 and raw_target is not None and not is_super_over:
                warnings.append(
                    Issue(
                        code="first_innings_has_target",
                        message="first regulation innings includes a target in the source",
                        innings_number=index,
                    )
                )

        _check_raw_deliveries(raw, index, errors)


def _check_raw_deliveries(raw: dict[str, Any], innings_number: int, errors: list[Issue]) -> None:
    seen_overs: set[int] = set()
    previous_over: int | None = None
    for over in raw.get("overs") or []:
        if not isinstance(over, dict):
            continue
        over_number = over.get("over")
        if isinstance(over_number, int):
            if over_number in seen_overs:
                errors.append(
                    Issue(
                        code="duplicate_over",
                        message=f"raw innings has duplicate over {over_number}",
                        innings_number=innings_number,
                    )
                )
            if previous_over is not None and over_number < previous_over:
                errors.append(
                    Issue(
                        code="out_of_order_over",
                        message=f"raw over {over_number} appears after {previous_over}",
                        innings_number=innings_number,
                    )
                )
            seen_overs.add(over_number)
            previous_over = over_number
        for delivery in over.get("deliveries") or []:
            if not isinstance(delivery, dict):
                continue
            runs = delivery.get("runs") or {}
            batter = runs.get("batter", runs.get("batsman"))
            extras = runs.get("extras")
            total = runs.get("total")
            if batter is not None and extras is not None and total is not None:
                try:
                    if int(batter) + int(extras) != int(total):
                        errors.append(
                            Issue(
                                code="raw_runs_components_mismatch",
                                message=f"raw batter {batter} + extras {extras} != total {total}",
                                innings_number=innings_number,
                            )
                        )
                except (TypeError, ValueError):
                    errors.append(
                        Issue(
                            code="raw_runs_not_numeric",
                            message="raw delivery runs are not numeric",
                            innings_number=innings_number,
                        )
                    )


def _source_innings_totals(
    innings: NormalizedInnings,
    raw_innings: list[Any] | None,
    errors: list[Issue],
) -> dict[str, int | None]:
    if raw_innings is not None:
        if len(raw_innings) < innings.innings_number:
            errors.append(
                Issue(
                    code="raw_innings_missing",
                    message="raw document is missing this innings",
                    innings_number=innings.innings_number,
                )
            )
            return _empty_source_totals()
        raw = raw_innings[innings.innings_number - 1]
        if not isinstance(raw, dict):
            return _empty_source_totals()
        return _sum_raw_innings(raw)

    return _sum_normalized_innings(innings)


def _empty_source_totals() -> dict[str, int | None]:
    return {
        "runs": 0,
        "wicket_events": 0,
        "wickets": 0,
        "legal_balls": 0,
        "deliveries": 0,
        "target_runs": None,
    }


def _sum_normalized_innings(innings: NormalizedInnings) -> dict[str, int | None]:
    runs = innings.penalty_runs.pre + innings.penalty_runs.post
    wicket_events = 0
    wickets = 0
    legal_balls = 0
    deliveries = 0
    for delivery in innings.deliveries:
        deliveries += 1
        runs += delivery.total_runs
        legal_balls += 1 if delivery.is_legal_delivery else 0
        wicket_events += len(delivery.wickets)
        wickets += sum(1 for wicket in delivery.wickets if wicket.counts_as_wicket)
    return {
        "runs": runs,
        "wicket_events": wicket_events,
        "wickets": wickets,
        "legal_balls": legal_balls,
        "deliveries": deliveries,
        "target_runs": innings.target.runs if innings.target else None,
    }


def _sum_raw_innings(raw: dict[str, Any]) -> dict[str, int | None]:
    penalty = raw.get("penalty_runs") or {}
    runs = int(penalty.get("pre") or 0) + int(penalty.get("post") or 0)
    wicket_events = 0
    wickets = 0
    legal_balls = 0
    deliveries = 0
    for over in raw.get("overs") or []:
        for delivery in over.get("deliveries") or []:
            deliveries += 1
            runs += int((delivery.get("runs") or {}).get("total") or 0)
            extras = delivery.get("extras") or {}
            if is_legal_delivery(extras):
                legal_balls += 1
            raw_wickets = delivery.get("wickets") or []
            wicket_events += len(raw_wickets)
            wickets += sum(1 for wicket in raw_wickets if counts_as_wicket(wicket.get("kind")))
    target = (raw.get("target") or {}).get("runs") if isinstance(raw.get("target"), dict) else None
    return {
        "runs": runs,
        "wicket_events": wicket_events,
        "wickets": wickets,
        "legal_balls": legal_balls,
        "deliveries": deliveries,
        "target_runs": int(target) if target is not None else None,
    }


def _reconstructed_innings_totals(
    innings: NormalizedInnings,
    states: list[Any],
) -> dict[str, int | None]:
    innings_states = [state for state in states if state.innings_number == innings.innings_number]
    finalized = [
        state
        for state in innings_states
        if state.knowledge_horizon == KnowledgeHorizon.AFTER_INNINGS
    ]
    if finalized:
        state = finalized[-1]
    elif innings_states:
        state = innings_states[-1]
    else:
        return {
            "runs": innings.penalty_runs.pre + innings.penalty_runs.post,
            "wicket_events": 0,
            "wickets": 0,
            "legal_balls": 0,
            "deliveries": 0,
            "target_runs": innings.target.runs if innings.target else None,
        }
    return {
        "runs": state.innings_runs,
        "wicket_events": state.innings_wicket_events,
        "wickets": state.innings_wickets,
        "legal_balls": state.legal_balls,
        "deliveries": state.total_deliveries,
        "target_runs": innings.target.runs if innings.target else None,
    }


def _check_normalized_delivery_consistency(innings: NormalizedInnings, errors: list[Issue]) -> None:
    for delivery in innings.deliveries:
        if delivery.batter_runs + delivery.extras_runs != delivery.total_runs:
            errors.append(
                Issue(
                    code="runs_components_mismatch",
                    message=(
                        f"batter {delivery.batter_runs} + extras {delivery.extras_runs} "
                        f"!= total {delivery.total_runs}"
                    ),
                    innings_number=innings.innings_number,
                    sequence=delivery.sequence,
                )
            )
        extras_named_total = delivery.extras.total
        if extras_named_total and extras_named_total != delivery.extras_runs:
            if extras_named_total > delivery.extras_runs:
                errors.append(
                    Issue(
                        code="extras_over_total",
                        message="named extras exceed runs.extras",
                        innings_number=innings.innings_number,
                        sequence=delivery.sequence,
                    )
                )


def _compare_counts(report: InningsValidation, errors: list[Issue]) -> None:
    checks = (
        ("runs_mismatch", report.source_runs, report.reconstructed_runs),
        ("wicket_events_mismatch", report.source_wicket_events, report.reconstructed_wicket_events),
        ("wickets_mismatch", report.source_counting_wickets, report.reconstructed_wickets),
        ("legal_balls_mismatch", report.source_legal_balls, report.reconstructed_legal_balls),
        ("deliveries_mismatch", report.source_deliveries, report.reconstructed_deliveries),
    )
    for code, source_value, reconstructed_value in checks:
        if source_value != reconstructed_value:
            errors.append(
                Issue(
                    code=code,
                    message=f"{code}: source={source_value} reconstructed={reconstructed_value}",
                    innings_number=report.innings_number,
                )
            )
    if (
        report.source_target_runs is not None
        and report.reconstructed_target_runs is not None
        and report.source_target_runs != report.reconstructed_target_runs
    ):
        errors.append(
            Issue(
                code="target_mismatch",
                message=(
                    f"target mismatch: source={report.source_target_runs} "
                    f"reconstructed={report.reconstructed_target_runs}"
                ),
                innings_number=report.innings_number,
            )
        )


def _add_outcome_warnings(
    match: NormalizedMatch,
    reports: list[InningsValidation],
    warnings: list[Issue],
) -> None:
    outcome = match.info.outcome
    if outcome.method or outcome.result:
        return
    regulation = [report for report in reports if not report.is_super_over]
    if len(regulation) != 2 or outcome.win_by_runs is None or not outcome.winner:
        return
    first, second = regulation
    if first.batting_team != outcome.winner:
        return
    margin = first.reconstructed_runs - second.reconstructed_runs
    if margin != outcome.win_by_runs:
        warnings.append(
            Issue(
                code="outcome_margin_differs",
                message=(
                    f"source win margin {outcome.win_by_runs} runs differs from "
                    f"reconstructed {margin} runs"
                ),
            )
        )
