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
from app.services.explanations.classifier import classify_question
from app.services.explanations.context import (
    build_explanation_context,
    validate_context,
)
from app.services.explanations.deterministic import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROVIDER,
    answer_question,
)
from app.services.explanations.fallback import (
    FALLBACK_MODEL,
    FALLBACK_PROVIDER,
    build_verified_facts_fallback,
    fallback_reason_for,
    is_fallback_eligible,
)
from app.services.explanations.guard import GeminiRequestManager
from app.services.explanations.parser import parse_explanation_json, to_response
from app.services.explanations.prompts import build_prompts, prompt_payload_size_chars
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
        question: str | None = None,
    ) -> ExplanationResponse:
        loaded = self.catalog.get(match_id)
        state = loaded.state_at(sequence)
        context_started = time.monotonic()
        context = build_explanation_context(loaded, state, self.artifact)
        validate_context(context)
        context_ms = int((time.monotonic() - context_started) * 1000)
        request_id = uuid.uuid4().hex[:12]
        # Classification uses a normalized copy. Gemini always receives the
        # original question text unchanged.
        classification = classify_question(question)
        if classification.use_deterministic:
            payload = answer_question(
                category=classification.category,
                context=context,
                state=state,
                audience_level=audience_level,
            )
            response = to_response(
                payload,
                context=context,
                audience_level=audience_level,
                provider_name=DETERMINISTIC_PROVIDER,
                model_name=DETERMINISTIC_MODEL,
                explanation_source="deterministic",
            )
            log_event(
                logger,
                "deterministic_explanation_generated",
                match_id=match_id,
                sequence=context.sequence,
                audience=audience_level.value,
                category=classification.category.value,
                certainty=classification.certainty.value,
                request_id=request_id,
                model=DETERMINISTIC_MODEL,
                context_ms=context_ms,
            )
            return response

        manager = self.request_manager
        if manager is None or getattr(self.provider, "name", None) != "gemini":
            return self._generate(
                audience_level,
                context,
                request_id,
                question,
                context_ms=context_ms,
            )

        model_id = None
        if self.artifact is not None:
            model_id = self.artifact.metadata.model_id
        cache_key = explanation_cache_key(
            match_id=match_id,
            sequence=context.sequence,
            audience_level=audience_level,
            model_id=model_id,
            question=question,
            provider_name=self.provider.name,
            llm_model=self.provider.model_name,
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
                context_ms=context_ms,
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
            classification_reason=classification.reason,
            certainty=classification.certainty.value,
            context_ms=context_ms,
        )

        def produce() -> ExplanationResponse:
            try:
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
                            context_ms=context_ms,
                        )
                        return replay
                    response = self._generate(
                        audience_level,
                        context,
                        request_id,
                        question,
                        context_ms=context_ms,
                    )
                    stored = manager.cache.put(cache_key, response)
                    log_event(
                        logger,
                        "gemini_cache_store",
                        match_id=match_id,
                        sequence=context.sequence,
                        request_id=request_id,
                        stored=stored,
                        explanation_source=response.explanation_source,
                        degraded=response.degraded,
                    )
                    return response
            except (ProviderError, ExplanationError) as exc:
                if not is_fallback_eligible(exc):
                    raise
                return self._fallback_response(
                    audience_level,
                    context,
                    request_id,
                    question,
                    exc,
                    context_ms=context_ms,
                )

        return manager.cache.coalesce(cache_key, produce)

    def _generate(
        self,
        audience_level: AudienceLevel,
        context: ExplanationContext,
        request_id: str,
        question: str | None = None,
        *,
        context_ms: int | None = None,
    ) -> ExplanationResponse:
        compact_chars = prompt_payload_size_chars(context, compact=True)
        full_chars = prompt_payload_size_chars(context, compact=False)
        system_prompt, user_prompt = build_prompts(
            audience_level, context, question=question
        )
        started = time.monotonic()
        log_event(
            logger,
            "gemini_prompt_prepared",
            match_id=context.source_match_id,
            sequence=context.sequence,
            request_id=request_id,
            model=self.provider.model_name,
            context_chars_compact=compact_chars,
            context_chars_full=full_chars,
            prompt_chars=len(system_prompt) + len(user_prompt),
            context_ms=context_ms,
        )
        try:
            raw = self.provider.generate_json(system_prompt, user_prompt)
            payload = parse_explanation_json(raw)
        except (ProviderError, ExplanationError) as exc:
            log_event(
                logger,
                "explanation_provider_failed",
                match_id=context.source_match_id,
                sequence=context.sequence,
                duration_ms=int((time.monotonic() - started) * 1000),
                provider=self.provider.name,
                model=self.provider.model_name,
                request_id=request_id,
                error_code=getattr(exc, "code", "provider_error"),
                error_status=getattr(exc, "status_code", None),
            )
            if is_fallback_eligible(exc):
                return self._fallback_response(
                    audience_level,
                    context,
                    request_id,
                    question,
                    exc,
                    context_ms=context_ms,
                )
            raise
        except Exception:
            wrapped = ProviderError(
                "LLM provider failed",
                code="provider_error",
                status_code=502,
            )
            log_event(
                logger,
                "explanation_provider_failed",
                match_id=context.source_match_id,
                sequence=context.sequence,
                duration_ms=int((time.monotonic() - started) * 1000),
                provider=self.provider.name,
                model=self.provider.model_name,
                request_id=request_id,
                error_code=wrapped.code,
                error_status=wrapped.status_code,
            )
            return self._fallback_response(
                audience_level,
                context,
                request_id,
                question,
                wrapped,
                context_ms=context_ms,
            )
        response = to_response(
            payload,
            context=context,
            audience_level=audience_level,
            provider_name=self.provider.name,
            model_name=self.provider.model_name,
            explanation_source="gemini",
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
            prompt_chars=len(system_prompt) + len(user_prompt),
            explanation_source="gemini",
        )
        return response

    def _fallback_response(
        self,
        audience_level: AudienceLevel,
        context: ExplanationContext,
        request_id: str,
        question: str | None,
        exc: Exception,
        *,
        context_ms: int | None = None,
    ) -> ExplanationResponse:
        reason = fallback_reason_for(exc)
        payload = build_verified_facts_fallback(
            context=context,
            audience_level=audience_level,
            reason=reason,
            question=question,
        )
        response = to_response(
            payload,
            context=context,
            audience_level=audience_level,
            provider_name=FALLBACK_PROVIDER,
            model_name=FALLBACK_MODEL,
            explanation_source="fallback",
            degraded=True,
            fallback_reason=reason,
        )
        log_event(
            logger,
            "explanation_fallback_served",
            match_id=context.source_match_id,
            sequence=context.sequence,
            audience=audience_level.value,
            request_id=request_id,
            fallback_reason=reason,
            error_code=getattr(exc, "code", None),
            error_status=getattr(exc, "status_code", None),
            context_ms=context_ms,
            explanation_source="fallback",
            degraded=True,
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
