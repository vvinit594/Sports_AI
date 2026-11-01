"""Shared HTTP client with bounded retries for LLM providers."""

from __future__ import annotations

import logging
import time

import httpx

from app.core.exceptions import ProviderError

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class JsonHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_retries: int,
        transport: httpx.BaseTransport | None = None,
    ):
        self.max_retries = max_retries
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, object]:
        attempts = self.max_retries + 1
        last_status: int | None = None
        for attempt in range(attempts):
            try:
                response = self._client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                raise ProviderError(
                    "LLM provider timed out",
                    code="timeout",
                    status_code=504,
                ) from exc
            except httpx.TransportError as exc:
                if attempt + 1 < attempts:
                    time.sleep(_backoff(attempt))
                    continue
                raise ProviderError(
                    "LLM provider unavailable",
                    code="provider_unavailable",
                    status_code=503,
                ) from exc

            last_status = response.status_code
            if response.status_code in (401, 403):
                raise ProviderError(
                    "LLM provider rejected credentials",
                    code="invalid_credentials",
                    status_code=502,
                )
            if response.status_code in RETRYABLE_STATUS and attempt + 1 < attempts:
                logger.info(
                    "retrying LLM provider status=%s attempt=%s",
                    response.status_code,
                    attempt + 1,
                )
                time.sleep(_retry_after(response, attempt))
                continue
            if response.status_code == 429:
                raise ProviderError(
                    "LLM provider rate limited",
                    code="rate_limited",
                    status_code=429,
                )
            if response.status_code >= 400:
                raise ProviderError(
                    "LLM provider request failed",
                    code="provider_error",
                    status_code=502,
                )
            try:
                body = response.json()
            except ValueError as exc:
                raise ProviderError(
                    "LLM provider returned non-JSON",
                    code="malformed_output",
                    status_code=502,
                ) from exc
            if not isinstance(body, dict):
                raise ProviderError(
                    "LLM provider returned a non-object payload",
                    code="malformed_output",
                    status_code=502,
                )
            return body

        raise ProviderError(
            f"LLM provider request failed after retries (status={last_status})",
            code="provider_error",
            status_code=502,
        )


def _backoff(attempt: int) -> float:
    return min(0.25 * (2**attempt), 2.0)


def _retry_after(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return min(float(header), 5.0)
        except ValueError:
            pass
    return _backoff(attempt)
