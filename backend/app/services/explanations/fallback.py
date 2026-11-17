"""Verified-facts fallback when the LLM provider cannot answer.

Never invents cricket values. Never presents tactical interpretation as fact.
Never claims to be a Gemini explanation.
"""

from __future__ import annotations

from app.core.exceptions import ExplanationError, ProviderError
from app.schemas.explanation import (
    AudienceLevel,
    ExplanationContext,
    LLMExplanationPayload,
)
from app.services.explanations.deterministic import (
    DETERMINISTIC_MODEL,
    HISTORICAL_NOTE,
    _delivery_brief,
    _fmt_optional_int,
    _fmt_rate,
    _match_context,
    _moment_brief,
    _score_line,
)

FALLBACK_PROVIDER = "deterministic"
FALLBACK_MODEL = DETERMINISTIC_MODEL

# Provider / parse failures that may degrade to verified facts (HTTP 200).
# Incomplete match context and validation errors still raise.
_FALLBACK_ELIGIBLE_CODES = frozenset(
    {
        "rate_limited",
        "timeout",
        "provider_unavailable",
        "provider_error",
        "malformed_output",
        "content_blocked",
        "unsupported_model",
        "invalid_request",
        "invalid_credentials",
        "application_rate_limited",
        "daily_budget_exhausted",
    }
)

_REASON_LABELS = {
    "rate_limited": "provider_rate_limited",
    "application_rate_limited": "application_rate_limited",
    "daily_budget_exhausted": "daily_budget_exhausted",
    "timeout": "provider_timeout",
    "provider_unavailable": "provider_unavailable",
    "provider_error": "provider_error",
    "malformed_output": "malformed_provider_output",
    "content_blocked": "content_blocked",
    "unsupported_model": "unsupported_model",
    "invalid_request": "invalid_provider_request",
    "invalid_credentials": "invalid_credentials",
}


def is_fallback_eligible(exc: Exception) -> bool:
    if isinstance(exc, ProviderError):
        return exc.code in _FALLBACK_ELIGIBLE_CODES
    if isinstance(exc, ExplanationError):
        return exc.code in _FALLBACK_ELIGIBLE_CODES
    return False


def fallback_reason_for(exc: Exception) -> str:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code in _REASON_LABELS:
        return _REASON_LABELS[code]
    return "provider_unavailable"


def build_verified_facts_fallback(
    *,
    context: ExplanationContext,
    audience_level: AudienceLevel,
    reason: str,
    question: str | None = None,
) -> LLMExplanationPayload:
    """Assemble grounded scoreboard facts without interpretive claims."""

    score = _score_line(context)
    overs = context.overs or "unknown"
    batting = context.batting_team or "unknown"
    bowling = context.bowling_team or "unknown"
    target = _fmt_optional_int(context.target, "unknown")
    runs_remaining = _fmt_optional_int(context.runs_remaining, "unknown")
    crr = _fmt_rate(context.current_run_rate)
    rrr = _fmt_rate(context.required_run_rate)

    summary = (
        "AI explanation is temporarily unavailable. "
        f"Verified reconstructed score: {score} after {overs} overs."
    )
    what_parts = [
        f"{batting} batting against {bowling}.",
        f"Score {score} after {overs} overs.",
        f"Target {target}; runs remaining {runs_remaining}.",
        f"Current run rate {crr}; required run rate {rrr}.",
    ]
    if context.last_delivery is not None:
        what_parts.append(f"Last delivery: {_delivery_brief(context.last_delivery)}")
    elif "last_delivery" in context.unknown_fields:
        what_parts.append("Last delivery: unknown.")
    if context.recent_deliveries:
        recent = " ".join(
            _delivery_brief(item) for item in context.recent_deliveries[-3:]
        )
        what_parts.append(f"Recent deliveries: {recent}")
    if context.significant_moments:
        top = context.significant_moments[0]
        what_parts.append(
            f"Detected significant moment (model-dependent): {_moment_brief(top)}"
        )
    if context.match_complete:
        what_parts.append(
            "Match complete: yes. Winner is only stated via the dedicated "
            "result question when source outcome data is present."
        )
    else:
        what_parts.append(
            "Match complete: no. PulseIQ will not invent a winner for an incomplete match."
        )
    if question:
        what_parts.append(
            "Your question needs AI interpretation that is unavailable right now; "
            "only verified reconstructed facts are shown."
        )

    if audience_level is AudienceLevel.BEGINNER:
        why = (
            "PulseIQ could not get an AI explanation, so it is showing only "
            "numbers already reconstructed from the historical match file. "
            "Missing values stay unknown."
        )
    elif audience_level is AudienceLevel.CASUAL:
        why = (
            "This is a degraded response: verified scoreboard facts only, "
            f"not an AI narrative (reason: {reason})."
        )
    else:
        why = (
            "Degraded mode. Values are copied from ExplanationContext / MatchState. "
            f"fallback_reason={reason}. No tactical analysis or predicted outcome."
        )

    factors = [
        f"Score: {score}",
        f"Overs: {overs}",
        f"Batting: {batting}",
        f"Bowling: {bowling}",
        f"Target: {target}",
        f"Runs remaining: {runs_remaining}",
        f"CRR: {crr}",
        f"RRR: {rrr}",
        f"Match complete: {'yes' if context.match_complete else 'no'}",
        f"Fallback reason: {reason}",
        HISTORICAL_NOTE,
    ]
    if context.unknown_fields:
        factors.append("Unknown fields: " + ", ".join(context.unknown_fields))

    return LLMExplanationPayload(
        summary=summary,
        what_happened=" ".join(what_parts),
        why_it_matters=why,
        match_context=_match_context(context, audience_level),
        key_factors=tuple(factors),
    )
