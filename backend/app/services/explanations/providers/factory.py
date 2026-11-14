"""Select one configured LLM provider from settings."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import ProviderError
from app.services.explanations.providers.base import LLMProvider
from app.services.explanations.providers.gemini import (
    GeminiProvider,
    resolve_gemini_model,
    safe_gemini_fallback_model,
)
from app.services.explanations.providers.mock import MockLLMProvider
from app.services.explanations.providers.openai import OpenAICompatibleProvider


def build_provider(settings: Settings) -> LLMProvider:
    name = settings.normalized_llm_provider()
    if name == "mock":
        return MockLLMProvider(model_name=settings.llm_model)
    if name == "gemini":
        if not settings.gemini_api_key:
            raise ProviderError(
                "LLM_PROVIDER=gemini requires GEMINI_API_KEY",
                code="provider_unavailable",
                status_code=503,
            )
        model_name = resolve_gemini_model(settings.llm_model)
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model_name=model_name,
            base_url=settings.gemini_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            fallback_model_name=safe_gemini_fallback_model(model_name),
        )
    if name in {"openai", "openai_compatible"}:
        if not settings.openai_api_key:
            raise ProviderError(
                "LLM_PROVIDER=openai requires OPENAI_API_KEY",
                code="provider_unavailable",
                status_code=503,
            )
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key,
            model_name=settings.llm_model,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    raise ProviderError(
        f"unsupported LLM_PROVIDER: {settings.llm_provider}",
        code="provider_unavailable",
        status_code=503,
    )


def provider_is_configured(settings: Settings) -> bool:
    name = settings.normalized_llm_provider()
    if name == "mock":
        return True
    if name == "gemini":
        return bool(settings.gemini_api_key)
    if name in {"openai", "openai_compatible"}:
        return bool(settings.openai_api_key)
    return False


def resolved_llm_model(settings: Settings) -> str:
    if settings.normalized_llm_provider() == "gemini":
        return resolve_gemini_model(settings.llm_model)
    return settings.llm_model
