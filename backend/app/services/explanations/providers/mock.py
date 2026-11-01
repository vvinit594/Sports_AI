"""Deterministic in-process provider used for tests and local development."""

from __future__ import annotations

import json
from typing import Any

from app.core.exceptions import ProviderError
from app.schemas.explanation import AudienceLevel


class MockLLMProvider:
    """Returns grounded JSON from the supplied context. Makes no network calls."""

    name = "mock"

    def __init__(self, model_name: str = "mock-explanations-v1"):
        self.model_name = model_name
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        context = _context_from_user_prompt(user_prompt)
        audience = _audience_from_user_prompt(user_prompt)
        batting = context.get("batting_team") or "The batting side"
        score = context.get("score")
        wickets = context.get("wickets")
        overs = context.get("overs")
        last_delivery = context.get("last_delivery") or {}
        total_runs = last_delivery.get("total_runs")
        wp = context.get("win_probability")
        notes = context.get("notes") or []

        facts: list[str] = []
        if score is not None and wickets is not None:
            facts.append(f"score is {score} for {wickets}")
        if overs is not None:
            facts.append(f"overs {overs}")
        if context.get("target") is not None:
            facts.append(f"target {context['target']}")
        if context.get("runs_remaining") is not None:
            facts.append(f"runs remaining {context['runs_remaining']}")
        if (
            wp is not None
            and isinstance(wp, dict)
            and wp.get("probability") is not None
        ):
            facts.append(f"model probability {wp['probability']}")
            if wp.get("evaluation_is_meaningful") is False:
                facts.append("this probability is not a production-accurate forecast")
        for note in notes:
            if isinstance(note, str) and note.strip():
                facts.append(note.strip())

        if audience == AudienceLevel.BEGINNER:
            summary = (
                f"{batting} has {score if score is not None else 'an unknown number of'} "
                "runs so far."
            )
            what = _beginner_what(last_delivery, total_runs)
            why = "This ball changes how much work is left in the innings."
            match_context = "Cricket here is a two-team game. One team is batting and trying to score runs."
        elif audience == AudienceLevel.CASUAL:
            summary = f"{batting} are {score}/{wickets} after {overs} overs."
            what = _casual_what(last_delivery, total_runs)
            why = "The latest ball shifts pressure on the chase or the defence."
            match_context = (
                _join_facts(facts) or "Match metrics for this ball are limited."
            )
        else:
            summary = (
                f"{batting} {score}/{wickets} in {overs}; "
                f"RRR={context.get('required_run_rate')}; "
                f"CRR={context.get('current_run_rate')}."
            )
            what = _advanced_what(context, last_delivery)
            why = (
                "Treat listed metrics as measured; any tactical reading is interpretation, "
                "not a new calculation."
            )
            match_context = (
                _join_facts(facts) or "Analytical inputs are incomplete for this state."
            )

        payload = {
            "summary": summary.strip(),
            "what_happened": what,
            "why_it_matters": why,
            "match_context": match_context,
            "key_factors": facts[:6] or ["supplied match context is limited"],
        }
        return json.dumps(payload)


def _context_from_user_prompt(user_prompt: str) -> dict[str, Any]:
    marker = "UNTRUSTED_MATCH_CONTEXT_JSON"
    start = user_prompt.find(marker)
    if start < 0:
        raise ProviderError(
            "mock provider did not receive match context",
            code="malformed_output",
            status_code=502,
        )
    json_start = user_prompt.find("{", start)
    json_end = user_prompt.rfind("}")
    if json_start < 0 or json_end <= json_start:
        raise ProviderError(
            "mock provider could not parse match context",
            code="malformed_output",
            status_code=502,
        )
    try:
        parsed = json.loads(user_prompt[json_start : json_end + 1])
    except json.JSONDecodeError as exc:
        raise ProviderError(
            "mock provider received invalid match context JSON",
            code="malformed_output",
            status_code=502,
        ) from exc
    if not isinstance(parsed, dict):
        raise ProviderError(
            "mock provider expected an object context",
            code="malformed_output",
            status_code=502,
        )
    return parsed


def _audience_from_user_prompt(user_prompt: str) -> AudienceLevel:
    lowered = user_prompt.lower()
    for level in AudienceLevel:
        if (
            f"audience_level={level.value}" in lowered
            or f"audience: {level.value}" in lowered
        ):
            return level
    return AudienceLevel.CASUAL


def _beginner_what(last_delivery: dict[str, Any], total_runs: object) -> str:
    kinds = last_delivery.get("wicket_kinds") or []
    if kinds:
        return "A batter got out on this ball."
    if total_runs == 0:
        return "No runs were scored on this ball."
    if isinstance(total_runs, int):
        return f"This ball added {total_runs} run{'s' if total_runs != 1 else ''}."
    return "The latest recorded ball is included in the supplied scoreboard."


def _casual_what(last_delivery: dict[str, Any], total_runs: object) -> str:
    kinds = last_delivery.get("wicket_kinds") or []
    if kinds:
        return f"Wicket event ({', '.join(str(item) for item in kinds)}) on the latest ball."
    if last_delivery.get("is_wide"):
        return "The latest ball was a wide."
    if last_delivery.get("is_noball"):
        return "The latest ball was a no-ball."
    if isinstance(total_runs, int):
        return f"The latest ball scored {total_runs}."
    return "The latest ball is recorded without a complete run breakdown."


def _advanced_what(context: dict[str, Any], last_delivery: dict[str, Any]) -> str:
    parts = [
        f"sequence {context.get('sequence')}",
        f"legal balls {context.get('legal_balls')}",
        f"balls remaining {context.get('balls_remaining')}",
        f"wickets remaining {context.get('wickets_remaining')}",
    ]
    if last_delivery:
        parts.append(f"last ball runs {last_delivery.get('total_runs')}")
    return "; ".join(str(item) for item in parts)


def _join_facts(facts: list[str]) -> str:
    return "; ".join(facts)
