"""Google Gemini REST provider. Uses httpx, not a vendor SDK."""

from __future__ import annotations

from app.core.exceptions import ProviderError
from app.services.explanations.providers.http import JsonHttpClient


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
    ):
        if not api_key.strip():
            raise ProviderError(
                "Gemini provider is not configured",
                code="provider_unavailable",
                status_code=503,
            )
        self.model_name = model_name
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}/models/{model_name}:generateContent"
        self._client = client or JsonHttpClient(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        payload: dict[str, object] = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        body = self._client.post_json(
            self._url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            payload=payload,
        )
        try:
            candidates = body["candidates"]
            content = candidates[0]["content"]
            parts = content["parts"]
            text = parts[0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "Gemini returned an unexpected payload",
                code="malformed_output",
                status_code=502,
            ) from exc
        if not isinstance(text, str) or not text.strip():
            raise ProviderError(
                "Gemini returned empty text",
                code="malformed_output",
                status_code=502,
            )
        return text
