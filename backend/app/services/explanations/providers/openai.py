"""OpenAI-compatible chat completions provider. Uses httpx, not a vendor SDK."""

from __future__ import annotations

from app.core.exceptions import ProviderError
from app.services.explanations.providers.http import JsonHttpClient


class OpenAICompatibleProvider:
    name = "openai"

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
                "OpenAI-compatible provider is not configured",
                code="provider_unavailable",
                status_code=503,
            )
        self.model_name = model_name
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._client = client or JsonHttpClient(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        payload: dict[str, object] = {
            "model": self.model_name,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        body = self._client.post_json(
            self._url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            payload=payload,
        )
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "OpenAI-compatible provider returned an unexpected payload",
                code="malformed_output",
                status_code=502,
            ) from exc
        if not isinstance(text, str) or not text.strip():
            raise ProviderError(
                "OpenAI-compatible provider returned empty text",
                code="malformed_output",
                status_code=502,
            )
        return text
