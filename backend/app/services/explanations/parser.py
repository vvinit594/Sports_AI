"""Parse and validate structured LLM explanation output."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import ValidationError

from app.core.exceptions import ExplanationError
from app.schemas.explanation import (
    AudienceLevel,
    ExplanationContext,
    ExplanationResponse,
    LLMExplanationPayload,
)


def parse_explanation_json(raw: str) -> LLMExplanationPayload:
    text = _strip_fences(raw).strip()
    if not text:
        raise ExplanationError(
            "LLM returned empty output",
            code="malformed_output",
            status_code=502,
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExplanationError(
            "LLM returned invalid JSON",
            code="malformed_output",
            status_code=502,
        ) from exc
    try:
        return LLMExplanationPayload.model_validate(payload)
    except ValidationError as exc:
        raise ExplanationError(
            "LLM output failed schema validation",
            code="malformed_output",
            status_code=502,
        ) from exc


def to_response(
    payload: LLMExplanationPayload,
    *,
    context: ExplanationContext,
    audience_level: AudienceLevel,
    provider_name: str,
    model_name: str,
) -> ExplanationResponse:
    return ExplanationResponse(
        summary=payload.summary,
        what_happened=payload.what_happened,
        why_it_matters=payload.why_it_matters,
        match_context=payload.match_context,
        key_factors=payload.key_factors,
        audience_level=audience_level,
        source_match_id=context.source_match_id,
        source_sequence=context.sequence,
        generated_at=datetime.now(UTC),
        model_provider=provider_name,
        model_name=model_name,
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
