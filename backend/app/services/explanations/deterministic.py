"""Deterministic cricket answers from reconstructed match evidence.

No Gemini call. No new scoring math. Missing values stay unknown.
"""

from __future__ import annotations

from app.schemas.explanation import (
    AudienceLevel,
    DeliverySnippet,
    ExplanationContext,
    LLMExplanationPayload,
    MomentEvidence,
)
from app.schemas.match import OutcomeInfo
from app.schemas.state import MatchState
from app.services.explanations.classifier import QuestionCategory

DETERMINISTIC_PROVIDER = "deterministic"
DETERMINISTIC_MODEL = "pulseiq-cricket-rules-v1"
HISTORICAL_NOTE = "This is a historical Cricsheet sample, not a live match."


def answer_question(
    *,
    category: QuestionCategory,
    context: ExplanationContext,
    state: MatchState,
    audience_level: AudienceLevel,
) -> LLMExplanationPayload:
    if category is QuestionCategory.SCORE_AND_MATCH_STATE:
        return _score_and_state(context, audience_level)
    if category is QuestionCategory.RUN_RATE:
        return _run_rate(context, audience_level)
    if category is QuestionCategory.DELIVERY_ANALYSIS:
        return _delivery(context, audience_level)
    if category is QuestionCategory.RECENT_PERFORMANCE:
        return _recent(context, audience_level)
    if category is QuestionCategory.SIGNIFICANT_MOMENTS:
        return _moments(context, audience_level)
    if category is QuestionCategory.TERMINAL_STATE:
        return _terminal(context, state, audience_level)
    return _unavailable(
        "PulseIQ cannot answer that from reconstructed match facts alone.",
        context,
        audience_level,
    )


def _score_and_state(
    context: ExplanationContext, audience: AudienceLevel
) -> LLMExplanationPayload:
    score = _score_line(context)
    batting = context.batting_team or "unknown"
    bowling = context.bowling_team or "unknown"
    innings = (
        f"innings {context.innings_number}"
        if context.innings_number is not None
        else "an unknown innings"
    )
    overs = context.overs or "unknown"
    target = _fmt_optional_int(context.target, "unknown")
    finished = (
        "yes, the reconstructed snapshot is complete"
        if context.match_complete
        else "no"
    )
    summary = f"{score} after {overs} overs."
    what = (
        f"{batting} are batting against {bowling} in {innings}. "
        f"The reconstructed score is {score} after {overs} overs."
    )
    if audience is AudienceLevel.BEGINNER:
        why = (
            "The score is the number of runs the batting team has, and wickets "
            "are batters who are out. Overs count how much of the innings has been used."
        )
    elif audience is AudienceLevel.CASUAL:
        why = "This is the reconstructed scoreboard at the selected delivery."
    else:
        why = (
            f"Verified scoreboard: {score}, overs {overs}, target {target}, "
            f"match complete={context.match_complete}."
        )
    factors = [
        f"Score: {score}",
        f"Overs: {overs}",
        f"Batting: {batting}",
        f"Innings: {context.innings_number if context.innings_number is not None else 'unknown'}",
        f"Target: {target}",
        f"Match complete: {finished}",
    ]
    return _payload(summary, what, why, context, audience, factors)


def _run_rate(
    context: ExplanationContext, audience: AudienceLevel
) -> LLMExplanationPayload:
    crr = _fmt_rate(context.current_run_rate)
    rrr = _fmt_rate(context.required_run_rate)
    runs_left = _fmt_optional_int(context.runs_remaining, "unknown")
    balls_left = _fmt_optional_int(context.balls_remaining, "unknown")
    summary = f"Current run rate {crr}; required run rate {rrr}."
    what = (
        f"Runs remaining {runs_left}. Balls remaining {balls_left}. "
        "These figures are copied from the reconstructed match state."
    )
    if audience is AudienceLevel.BEGINNER:
        why = (
            "Current run rate is how many runs the batting side has scored per over so far. "
            "Required run rate is how fast they still need to score to reach the target. "
            "If a figure is unknown, PulseIQ will not invent it."
        )
    elif audience is AudienceLevel.CASUAL:
        why = "Chase pressure comes from the gap between current and required run rate when both are known."
    else:
        wickets_left = _fmt_optional_int(context.wickets_remaining, "unknown")
        why = (
            f"CRR {crr}, RRR {rrr}, runs remaining {runs_left}, "
            f"balls remaining {balls_left}, wickets remaining {wickets_left}."
        )
    factors = [
        f"Current run rate: {crr}",
        f"Required run rate: {rrr}",
        f"Runs remaining: {runs_left}",
        f"Balls remaining: {balls_left}",
    ]
    return _payload(summary, what, why, context, audience, factors)


def _delivery(
    context: ExplanationContext, audience: AudienceLevel
) -> LLMExplanationPayload:
    delivery = context.last_delivery
    if delivery is None:
        return _unavailable(
            "No last-delivery record is available at this reconstructed sequence.",
            context,
            audience,
        )
    batter = delivery.batter or "unknown"
    bowler = delivery.bowler or "unknown"
    runs = _fmt_optional_int(delivery.total_runs, "unknown")
    extras = _fmt_optional_int(delivery.extras_runs, "unknown")
    wicket_text = (
        ", ".join(delivery.wicket_kinds) if delivery.wicket_kinds else "no wicket"
    )
    extras_kind = _extras_kind(delivery)
    summary = (
        f"{bowler} to {batter}: {runs} run(s) from the last reconstructed delivery."
    )
    what = (
        f"Batter {batter}, bowler {bowler}, total runs {runs}, extras {extras}"
        f"{', ' + extras_kind if extras_kind else ''}. Wicket: {wicket_text}."
    )
    if audience is AudienceLevel.BEGINNER:
        why = (
            "This is the last recorded ball in the reconstructed innings. "
            "A wide or no-ball is an extra, not a normal legal delivery."
        )
    elif audience is AudienceLevel.CASUAL:
        why = "The last ball is copied from the reconstructed delivery, including extras and any wicket kinds."
    else:
        legal = (
            "legal"
            if delivery.is_legal_delivery is True
            else "not legal"
            if delivery.is_legal_delivery is False
            else "unknown legality"
        )
        why = (
            f"Sequence {delivery.sequence}: {legal} delivery, batter runs "
            f"{_fmt_optional_int(delivery.batter_runs, 'unknown')}, extras {extras}."
        )
    factors = [
        f"Batter: {batter}",
        f"Bowler: {bowler}",
        f"Total runs: {runs}",
        f"Wicket: {wicket_text}",
        f"Wide: {_fmt_bool(delivery.is_wide)}",
        f"No-ball: {_fmt_bool(delivery.is_noball)}",
    ]
    return _payload(summary, what, why, context, audience, factors)


def _recent(
    context: ExplanationContext, audience: AudienceLevel
) -> LLMExplanationPayload:
    recent = context.recent_deliveries
    if not recent:
        return _unavailable(
            "No recent-delivery window is available at this reconstructed sequence.",
            context,
            audience,
        )
    runs = sum(item.total_runs or 0 for item in recent if item.total_runs is not None)
    wickets = sum(1 for item in recent if item.wicket_kinds)
    known_runs = all(item.total_runs is not None for item in recent)
    runs_text = str(runs) if known_runs else "unknown (some deliveries omit runs)"
    summary = (
        f"In the last {len(recent)} reconstructed deliveries: {runs_text} runs, "
        f"{wickets} wicket(s)."
    )
    what = " ".join(_delivery_brief(item) for item in recent)
    if audience is AudienceLevel.BEGINNER:
        why = (
            "PulseIQ looks at the last few recorded balls in this innings. "
            "It does not invent balls that are not in the reconstruction."
        )
    elif audience is AudienceLevel.CASUAL:
        why = "The recent window is the existing reconstructed delivery snippet, not a new calculation of form."
    else:
        why = (
            f"Window size {len(recent)} from reconstructed deliveries up to sequence "
            f"{context.sequence}."
        )
    factors = [
        f"Deliveries in window: {len(recent)}",
        f"Runs in window: {runs_text}",
        f"Wickets in window: {wickets}",
    ]
    return _payload(summary, what, why, context, audience, factors)


def _moments(
    context: ExplanationContext, audience: AudienceLevel
) -> LLMExplanationPayload:
    notes = " ".join(context.notes)
    if (
        "win probability unavailable" in notes.lower()
        and not context.significant_moments
    ):
        return _unavailable(
            "Significant moments are unavailable because win-probability evidence is not loaded.",
            context,
            audience,
        )
    if not context.significant_moments:
        return _unavailable(
            "No detector-identified significant moments are available up to this sequence.",
            context,
            audience,
        )
    top = max(
        context.significant_moments,
        key=lambda item: abs(item.probability_change or 0.0),
    )
    summary = (
        f"{len(context.significant_moments)} significant moment(s) detected up to "
        f"this sequence. Largest recorded change at sequence {top.sequence}."
    )
    what = " ".join(_moment_brief(item) for item in context.significant_moments)
    limitation = ""
    if context.win_probability and not context.win_probability.evaluation_is_meaningful:
        limitation = (
            " These probability changes are small-sample pipeline estimates, "
            "not production-accurate forecasts."
        )
    if audience is AudienceLevel.BEGINNER:
        why = (
            "A significant moment is a delivery where PulseIQ's existing detector "
            "saw a notable change in chase win probability." + limitation
        )
    elif audience is AudienceLevel.CASUAL:
        why = (
            "Moments come from the existing detector and available predictions, not a new model."
            + limitation
        )
    else:
        why = (
            f"Largest |probability_change| at sequence {top.sequence}: "
            f"{_fmt_rate(top.probability_change)}." + limitation
        )
    factors = [_moment_factor(item) for item in context.significant_moments]
    return _payload(summary, what, why, context, audience, factors)


def _terminal(
    context: ExplanationContext,
    state: MatchState,
    audience: AudienceLevel,
) -> LLMExplanationPayload:
    if not context.match_complete:
        return _unavailable(
            "The reconstructed snapshot is not a completed match, so PulseIQ will not state a winner.",
            context,
            audience,
        )
    outcome = state.outcome
    winner = outcome.winner
    if not winner:
        result = outcome.result or "unknown"
        summary = f"The reconstructed match is complete. Source result: {result}."
        what = (
            "No winner is recorded in the source outcome for this completed snapshot."
        )
        why = _terminal_why(audience, outcome)
        factors = [
            "Match complete: yes",
            f"Source result: {result}",
            "Winner: unknown",
        ]
        return _payload(summary, what, why, context, audience, factors)
    margin = _margin_text(outcome)
    summary = f"{winner} won this historical match{margin}."
    what = (
        f"Source outcome winner is {winner}. Reconstructed match_complete is true. "
        f"Final batting snapshot: {_score_line(context)} after {context.overs or 'unknown'} overs."
    )
    why = _terminal_why(audience, outcome)
    factors = [
        f"Winner: {winner}",
        f"Source result: {outcome.result or 'unknown'}",
        "Match complete: yes",
        f"Score snapshot: {_score_line(context)}",
    ]
    return _payload(summary, what, why, context, audience, factors)


def _terminal_why(audience: AudienceLevel, outcome: OutcomeInfo) -> str:
    if audience is AudienceLevel.BEGINNER:
        return (
            "The winner is taken from the historical match result, and only when "
            "the reconstructed match is marked complete."
        )
    if audience is AudienceLevel.CASUAL:
        method = outcome.method or "the recorded source result"
        return f"The result comes from {method} in the Cricsheet record, not from a live feed."
    return (
        f"Verified terminal fields only: winner={outcome.winner or 'unknown'}, "
        f"result={outcome.result or 'unknown'}, method={outcome.method or 'unknown'}."
    )


def _unavailable(
    message: str,
    context: ExplanationContext,
    audience: AudienceLevel,
) -> LLMExplanationPayload:
    why = (
        "PulseIQ only repeats reconstructed facts. It will not invent the missing value."
        if audience is AudienceLevel.BEGINNER
        else "The requested fact is not present in the reconstructed evidence."
    )
    return _payload(
        message,
        message,
        why,
        context,
        audience,
        ["Requested fact: unknown"],
    )


def _payload(
    summary: str,
    what_happened: str,
    why_it_matters: str,
    context: ExplanationContext,
    audience: AudienceLevel,
    key_factors: list[str],
) -> LLMExplanationPayload:
    match_context = _match_context(context, audience)
    return LLMExplanationPayload(
        summary=summary,
        what_happened=what_happened,
        why_it_matters=why_it_matters,
        match_context=match_context,
        key_factors=tuple(key_factors),
    )


def _match_context(context: ExplanationContext, audience: AudienceLevel) -> str:
    teams = " vs ".join(context.teams) if context.teams else "unknown teams"
    batting = context.batting_team or "unknown"
    if audience is AudienceLevel.BEGINNER:
        return (
            f"{teams}. {batting} are batting. {HISTORICAL_NOTE} "
            f"Sequence {context.sequence}."
        )
    return f"{teams}; batting {batting}; sequence {context.sequence}. {HISTORICAL_NOTE}"


def _score_line(context: ExplanationContext) -> str:
    runs = _fmt_optional_int(context.score, "unknown")
    wickets = _fmt_optional_int(context.wickets, "unknown")
    return f"{runs} for {wickets}"


def _fmt_optional_int(value: int | None, unknown: str) -> str:
    if value is None:
        return unknown
    return str(value)


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.2f}"


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def _extras_kind(delivery: DeliverySnippet) -> str:
    labels: list[str] = []
    if delivery.is_wide:
        labels.append("wide")
    if delivery.is_noball:
        labels.append("no-ball")
    return " and ".join(labels)


def _delivery_brief(item: DeliverySnippet) -> str:
    runs = _fmt_optional_int(item.total_runs, "unknown")
    wicket = f", wicket ({', '.join(item.wicket_kinds)})" if item.wicket_kinds else ""
    return f"Seq {item.sequence}: {runs} run(s){wicket}."


def _moment_brief(item: MomentEvidence) -> str:
    change = _fmt_rate(item.probability_change)
    return f"{item.moment_type} at sequence {item.sequence} (change {change})."


def _moment_factor(item: MomentEvidence) -> str:
    return f"{item.moment_type} @ {item.sequence}: {_fmt_rate(item.probability_change)}"


def _margin_text(outcome: OutcomeInfo) -> str:
    if outcome.win_by_runs is not None:
        return f" by {outcome.win_by_runs} runs"
    if outcome.win_by_wickets is not None:
        return f" by {outcome.win_by_wickets} wickets"
    if outcome.win_by_innings is not None:
        return f" by {outcome.win_by_innings} innings"
    return ""
