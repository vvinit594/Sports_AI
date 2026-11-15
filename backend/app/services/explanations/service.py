"""Explanation service. Independent of FastAPI route handlers."""

from __future__ import annotations

import logging
import time
import uuid

from app.core.exceptions import ExplanationError, ProviderError
from app.core.logging import log_event
from app.schemas.explanation import (
    AudienceLevel,
    ExplanationContext,
    ExplanationResponse,
)
from app.services.api.catalog import MatchCatalog
from app.services.explanations.cache import explanation_cache_key
from app.services.explanations.context import (
    build_explanation_context,
    validate_context,
)
from app.services.explanations.guard import GeminiRequestManager
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
        request_manager: GeminiRequestManager | None = None,
    ):
        self.catalog = catalog
        self.provider = provider
        self.artifact = artifact
        self.request_manager = request_manager

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
        request_id = uuid.uuid4().hex[:12]
        manager = self.request_manager
        if manager is None or getattr(self.provider, "name", None) != "gemini":
            return self._generate(audience_level, context, request_id)

        model_id = None
        if self.artifact is not None:
            model_id = self.artifact.metadata.model_id
        cache_key = explanation_cache_key(
            match_id=match_id,
            sequence=context.sequence,
            audience_level=audience_level,
            model_id=model_id,
        )
        cached = manager.cache.get(cache_key)
        if cached is not None:
            log_event(
                logger,
                "gemini_cache_hit",
                match_id=match_id,
                sequence=context.sequence,
                audience=audience_level.value,
                request_id=request_id,
                model=self.provider.model_name,
            )
            return cached
        log_event(
            logger,
            "gemini_cache_miss",
            match_id=match_id,
            sequence=context.sequence,
            audience=audience_level.value,
            request_id=request_id,
            model=self.provider.model_name,
        )

        def produce() -> ExplanationResponse:
            with manager.gate:
                replay = manager.cache.get(cache_key)
                if replay is not None:
                    log_event(
                        logger,
                        "gemini_cache_hit",
                        match_id=match_id,
                        sequence=context.sequence,
                        audience=audience_level.value,
                        request_id=request_id,
                        model=self.provider.model_name,
                    )
                    return replay
                response = self._generate(audience_level, context, request_id)
                manager.cache.put(cache_key, response)
                return response

        return manager.cache.coalesce(cache_key, produce)

    def _generate(
        self,
        audience_level: AudienceLevel,
        context: ExplanationContext,
        request_id: str,
    ) -> ExplanationResponse:
        system_prompt, user_prompt = build_prompts(audience_level, context)
        started = time.monotonic()
        try:
            raw = self.provider.generate_json(system_prompt, user_prompt)
        except ProviderError:
            log_event(
                logger,
                "explanation_provider_failed",
                match_id=context.source_match_id,
                sequence=context.sequence,
                duration_ms=int((time.monotonic() - started) * 1000),
                provider=self.provider.name,
                model=self.provider.model_name,
                request_id=request_id,
            )
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
            match_id=context.source_match_id,
            sequence=context.sequence,
            audience=audience_level.value,
            provider=self.provider.name,
            model=self.provider.model_name,
            duration_ms=int((time.monotonic() - started) * 1000),
            request_id=request_id,
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
