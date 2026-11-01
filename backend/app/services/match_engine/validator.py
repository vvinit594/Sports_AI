"""Validate reconstructed match totals against Cricsheet source records."""

from __future__ import annotations

from typing import Any

from app.core.cricket_rules import counts_as_wicket, is_legal_delivery
from app.schemas.match import NormalizedInnings, NormalizedMatch
from app.schemas.validation import InningsValidation, Issue, ValidationReport
from app.services.match_engine.engine import MatchStateEngine


def validate_match(
    match: NormalizedMatch,
    raw: dict[str, Any] | None = None,
) -> ValidationReport:
    """Compare reconstructed innings totals with source delivery sums.

    When `raw` is provided, totals are also re-summed directly from the
    original Cricsheet JSON so parser omissions are visible.
    """

    engine = MatchStateEngine(match)
    states = engine.reconstruct()
    errors: list[Issue] = []
    warnings: list[Issue] = []
    innings_reports: list[InningsValidation] = []

    raw_innings = (raw or {}).get("innings") if raw else None
    if raw is not None and not isinstance(raw_innings, list):
        errors.append(Issue(code="raw_innings_missing", message="raw document has no innings array"))
        raw_innings = []

    for innings in match.innings:
        source = _source_innings_totals(innings, raw_innings)
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
                # Unknown extra types can make named extras < extras_runs.
                if extras_named_total > delivery.extras_runs:
                    errors.append(
                        Issue(
                            code="extras_over_total",
                            message="named extras exceed runs.extras",
                            innings_number=innings.innings_number,
                            sequence=delivery.sequence,
                        )
                    )
                else:
                    warnings.append(
                        Issue(
                            code="unnamed_extra_runs",
                            message="runs.extras contains more than the named extra fields",
                            innings_number=innings.innings_number,
                            sequence=delivery.sequence,
                        )
                    )

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


def _source_innings_totals(
    innings: NormalizedInnings,
    raw_innings: list[Any] | None,
) -> dict[str, int | None]:
    if raw_innings is not None and len(raw_innings) >= innings.innings_number:
        raw = raw_innings[innings.innings_number - 1]
        if isinstance(raw, dict):
            return _sum_raw_innings(raw)

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
    target = (raw.get("target") or {}).get("runs")
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
    completed = [
        state
        for state in states
        if state.innings_number == innings.innings_number and state.innings_just_completed
    ]
    if completed:
        state = completed[-1]
        return {
            "runs": state.innings_runs,
            "wicket_events": state.innings_wicket_events,
            "wickets": state.innings_wickets,
            "legal_balls": state.legal_balls,
            "deliveries": state.total_deliveries,
            "target_runs": innings.target.runs if innings.target else None,
        }
    return {
        "runs": innings.penalty_runs.pre + innings.penalty_runs.post,
        "wicket_events": 0,
        "wickets": 0,
        "legal_balls": 0,
        "deliveries": 0,
        "target_runs": innings.target.runs if innings.target else None,
    }


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
