"""Explanation service. Independent of FastAPI route handlers."""

from __future__ import annotations

import logging

from app.core.exceptions import ExplanationError, ProviderError
from app.core.logging import log_event
from app.schemas.explanation import AudienceLevel, ExplanationResponse
from app.services.api.catalog import MatchCatalog
from app.services.explanations.context import (
    build_explanation_context,
    validate_context,
)
from app.services.explanations.parser import parse_explanation_json, to_response
from app.services.explanations.prompts import build_prompts
from app.services.explanations.providers.base import LLMProvider
from app.services.ml.model_registry import ModelArtifact

logger = logging.getLogger(__name__)


class ExplanationService:
    def __init__(
        self,
        catalog: MatchCatalog,
        provider: LLMProvider,
        artifact: ModelArtifact | None,
    ):
        self.catalog = catalog
        self.provider = provider
        self.artifact = artifact

    def explain(
        self,
        match_id: str,
        audience_level: AudienceLevel,
        sequence: int | None = None,
    ) -> ExplanationResponse:
        loaded = self.catalog.get(match_id)
        state = loaded.state_at(sequence)
        context = build_explanation_context(loaded, state, self.artifact)
        validate_context(context)
        system_prompt, user_prompt = build_prompts(audience_level, context)
        try:
            raw = self.provider.generate_json(system_prompt, user_prompt)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "LLM provider failed",
                code="provider_error",
                status_code=502,
            ) from exc
        payload = parse_explanation_json(raw)
        response = to_response(
            payload,
            context=context,
            audience_level=audience_level,
            provider_name=self.provider.name,
            model_name=self.provider.model_name,
        )
        log_event(
            logger,
            "explanation_generated",
            match_id=match_id,
            sequence=context.sequence,
            audience=audience_level.value,
            provider=self.provider.name,
        )
        return response


class UnavailableProvider:
    """Stand-in when the selected provider cannot be constructed."""

    name = "unavailable"
    model_name = "unavailable"

    def __init__(self, error: ProviderError):
        self._error = error

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        raise ExplanationError(
            str(self._error),
            code=self._error.code,
            status_code=self._error.status_code,
        ) from self._error
