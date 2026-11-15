"""Google Gemini REST provider. Uses httpx, not a vendor SDK."""

from __future__ import annotations

import logging
import time

from app.core.exceptions import ProviderError
from app.core.logging import log_event
from app.services.explanations.providers.http import JsonHttpClient

logger = logging.getLogger(__name__)

_GEMINI_USER_MESSAGES = {
    "timeout": (
        "PulseIQ could not finish this explanation in time. "
        "Your match context is preserved."
    ),
    "rate_limited": "Gemini has reached its request limit. Please wait before trying again.",
    "provider_unavailable": (
        "Gemini is temporarily unavailable. Your match context is preserved. "
        "Please try again later."
    ),
    "provider_error": (
        "Gemini is temporarily unavailable. Your match context is preserved. "
        "Please try again later."
    ),
}

# Stable Gemini API Flash model as of the Gemini API model catalog
# (https://ai.google.dev/gemini-api/docs/models). Gemini 2.0 Flash shut down
# on 1 June 2026 and must not be used as a default or fallback.
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

_BLOCKED_FINISH_REASONS = frozenset(
    {
        "SAFETY",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "RECITATION",
        "SPII",
        "IMAGE_SAFETY",
    }
)
_PLACEHOLDER_MODELS = frozenset(
    {
        "",
        "mock",
        "mock-explanations-v1",
    }
)
SHUTDOWN_GEMINI_MODELS = frozenset(
    {
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-lite-preview",
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-2.0-flash-live-001",
        "gemini-2.0-flash-preview-image-generation",
    }
)


def _normalize_model_id(model_name: str | None) -> str:
    raw = (model_name or "").strip()
    if raw.lower().startswith("models/"):
        raw = raw[7:].strip()
    return raw


def is_shutdown_gemini_model(model_name: str | None) -> bool:
    return _normalize_model_id(model_name).lower() in SHUTDOWN_GEMINI_MODELS


def resolve_gemini_model(model_name: str | None) -> str:
    """Resolve a Gemini model id without selecting a shut-down model.

    Placeholder ids (empty, mock) are replaced with the current default.
    Shut-down ids such as gemini-2.0-flash are also replaced because they
    cannot serve generateContent. Any other explicit id, including a
    deprecated-but-still-configured model, is left unchanged.
    """

    raw = _normalize_model_id(model_name)
    lowered = raw.lower()
    if not raw or lowered in _PLACEHOLDER_MODELS or lowered.startswith("mock"):
        return DEFAULT_GEMINI_MODEL
    if lowered in SHUTDOWN_GEMINI_MODELS:
        return DEFAULT_GEMINI_MODEL
    return raw


def safe_gemini_fallback_model(model_name: str) -> str | None:
    """Return a fallback id only when it is distinct and not shut down."""

    candidate = DEFAULT_GEMINI_MODEL
    if is_shutdown_gemini_model(candidate):
        return None
    if candidate == model_name:
        return None
    return candidate


def gemini_generate_url(base_url: str, model_name: str) -> str:
    return f"{base_url.rstrip('/')}/models/{model_name}:generateContent"


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str,
        timeout_seconds: float,
        max_retries: int,
        client: JsonHttpClient | None = None,
        fallback_model_name: str | None = None,
        request_deadline_seconds: float | None = None,
        request_manager: object | None = None,
        allow_model_fallback: bool = False,
    ):
        if not api_key.strip():
            raise ProviderError(
                "Gemini provider is not configured",
                code="provider_unavailable",
                status_code=503,
            )
        self.model_name = resolve_gemini_model(model_name)
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._url = gemini_generate_url(base_url, self.model_name)
        fallback = _normalize_model_id(fallback_model_name)
        if fallback and is_shutdown_gemini_model(fallback):
            fallback = DEFAULT_GEMINI_MODEL
        if (
            not fallback
            or fallback == self.model_name
            or is_shutdown_gemini_model(fallback)
        ):
            fallback = None
        self._fallback_model_name = fallback
        self._client = client or JsonHttpClient(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            request_deadline_seconds=request_deadline_seconds,
        )
        self._allow_model_fallback = allow_model_fallback
        if request_manager is not None:
            self.bind_request_manager(request_manager)

    def bind_request_manager(self, request_manager: object) -> None:
        bind = getattr(request_manager, "bind_http_client", None)
        if callable(bind):
            bind(self._client)

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        payload = _gemini_payload(system_prompt, user_prompt, self.model_name)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        attempted = self.model_name
        started = time.monotonic()
        try:
            body = self._client.post_json(self._url, headers=headers, payload=payload)
        except ProviderError as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            log_event(
                logger,
                "gemini_http_failed",
                model=attempted,
                code=exc.code,
                status=exc.status_code,
                duration_ms=duration_ms,
            )
            if (
                self._allow_model_fallback
                and exc.code == "unsupported_model"
                and self._fallback_model_name is not None
            ):
                logger.warning(
                    "Gemini model unavailable model=%s; using fallback model=%s",
                    attempted,
                    self._fallback_model_name,
                )
                fallback_url = gemini_generate_url(
                    self._base_url, self._fallback_model_name
                )
                try:
                    body = self._client.post_json(
                        fallback_url, headers=headers, payload=payload
                    )
                except ProviderError as fallback_exc:
                    raise _with_model_detail(
                        _user_facing_gemini_error(fallback_exc),
                        self._fallback_model_name,
                        attempted_model=attempted,
                    ) from fallback_exc
                self.model_name = self._fallback_model_name
            else:
                raise _with_model_detail(
                    _user_facing_gemini_error(exc), attempted
                ) from exc
        else:
            log_event(
                logger,
                "gemini_http_ok",
                model=self.model_name,
                status=200,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        return extract_gemini_text(body)


def _gemini_payload(
    system_prompt: str, user_prompt: str, model_name: str = ""
) -> dict[str, object]:
    generation_config: dict[str, object] = {
        "temperature": 0.2,
        "responseMimeType": "application/json",
        **_thinking_config(model_name),
    }
    return {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": generation_config,
    }


def _thinking_config(model_name: str) -> dict[str, object]:
    lowered = model_name.lower()
    if lowered.startswith("gemini-3"):
        return {"thinkingConfig": {"thinkingLevel": "LOW"}}
    if "2.5" in lowered:
        return {"thinkingConfig": {"thinkingBudget": 0}}
    return {}


def extract_gemini_text(body: dict[str, object]) -> str:
    feedback = body.get("promptFeedback")
    if isinstance(feedback, dict):
        reason = feedback.get("blockReason")
        if isinstance(reason, str) and reason and reason != "BLOCK_REASON_UNSPECIFIED":
            raise ProviderError(
                "Gemini blocked this explanation request",
                code="content_blocked",
                status_code=502,
            )

    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ProviderError(
            "Gemini returned empty text",
            code="malformed_output",
            status_code=502,
        )
    first = candidates[0]
    if not isinstance(first, dict):
        raise ProviderError(
            "Gemini returned an unexpected payload",
            code="malformed_output",
            status_code=502,
        )
    finish = first.get("finishReason")
    if isinstance(finish, str) and finish in _BLOCKED_FINISH_REASONS:
        raise ProviderError(
            "Gemini blocked this explanation request",
            code="content_blocked",
            status_code=502,
        )
    content = first.get("content")
    if not isinstance(content, dict):
        raise ProviderError(
            "Gemini returned an unexpected payload",
            code="malformed_output",
            status_code=502,
        )
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ProviderError(
            "Gemini returned an unexpected payload",
            code="malformed_output",
            status_code=502,
        )
    texts = [
        part["text"]
        for part in parts
        if isinstance(part, dict)
        and isinstance(part.get("text"), str)
        and part["text"].strip()
    ]
    if not texts:
        raise ProviderError(
            "Gemini returned empty text",
            code="malformed_output",
            status_code=502,
        )
    return texts[0] if len(texts) == 1 else "\n".join(texts)


def _user_facing_gemini_error(exc: ProviderError) -> ProviderError:
    message = _GEMINI_USER_MESSAGES.get(exc.code, str(exc))
    return ProviderError(
        message,
        code=exc.code,
        status_code=exc.status_code,
        detail=exc.detail,
        retry_after=getattr(exc, "retry_after", None),
    )


def _with_model_detail(
    exc: ProviderError,
    model_name: str,
    *,
    attempted_model: str | None = None,
) -> ProviderError:
    parts = [f"model={model_name}"]
    if attempted_model and attempted_model != model_name:
        parts.insert(0, f"attempted_model={attempted_model}")
    if exc.detail:
        parts.append(exc.detail)
    return ProviderError(
        str(exc),
        code=exc.code,
        status_code=exc.status_code,
        detail="; ".join(parts),
        retry_after=getattr(exc, "retry_after", None),
    )
