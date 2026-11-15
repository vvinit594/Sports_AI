"""Shared HTTP client with bounded retries for LLM providers."""

from __future__ import annotations

import logging
import random
import re
import time

import httpx

from app.core.exceptions import ProviderError

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|key|token|authorization|bearer)([\"']?\s*[:=]\s*)([^\s,;\"']+)"
)
_MIN_RETRY_BUDGET_SECONDS = 1.0


class JsonHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_retries: int,
        transport: httpx.BaseTransport | None = None,
        request_deadline_seconds: float | None = None,
        attempt_hook: object | None = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.request_deadline_seconds = (
            timeout_seconds
            if request_deadline_seconds is None
            else request_deadline_seconds
        )
        self.attempt_hook = attempt_hook
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def _run_attempt_hook(self) -> None:
        hook = self.attempt_hook
        if hook is None:
            return
        hook()

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, object],
    ) -> dict[str, object]:
        started = time.monotonic()
        deadline = started + self.request_deadline_seconds
        attempts = self.max_retries + 1
        last_status: int | None = None
        for attempt in range(attempts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError(
                    "PulseIQ could not finish this explanation in time. "
                    "Your match context is preserved.",
                    code="timeout",
                    status_code=504,
                )
            self._run_attempt_hook()
            attempt_timeout = min(self.timeout_seconds, remaining)
            try:
                response = self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=httpx.Timeout(
                        connect=min(5.0, attempt_timeout),
                        read=attempt_timeout,
                        write=min(10.0, attempt_timeout),
                        pool=min(5.0, attempt_timeout),
                    ),
                )
            except httpx.TimeoutException as exc:
                logger.warning(
                    "LLM provider attempt timed out attempt=%s remaining=%.2f",
                    attempt + 1,
                    deadline - time.monotonic(),
                )
                raise ProviderError(
                    "PulseIQ could not finish this explanation in time. "
                    "Your match context is preserved.",
                    code="timeout",
                    status_code=504,
                ) from exc
            except httpx.TransportError as exc:
                if attempt + 1 < attempts and _has_retry_budget(deadline):
                    time.sleep(_backoff(attempt))
                    continue
                raise ProviderError(
                    "LLM provider unavailable",
                    code="provider_unavailable",
                    status_code=503,
                ) from exc

            last_status = response.status_code
            if (
                response.status_code in RETRYABLE_STATUS
                and attempt + 1 < attempts
                and _has_retry_budget(deadline)
            ):
                delay = _retry_after(response, attempt)
                if deadline - time.monotonic() <= delay + _MIN_RETRY_BUDGET_SECONDS:
                    raise _http_error(response)
                logger.info(
                    "retrying LLM provider status=%s attempt=%s",
                    response.status_code,
                    attempt + 1,
                )
                time.sleep(delay)
                continue
            if response.status_code >= 400:
                raise _http_error(response)
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


def _has_retry_budget(deadline: float) -> bool:
    return deadline - time.monotonic() > _MIN_RETRY_BUDGET_SECONDS


def _parse_retry_after_seconds(response: httpx.Response) -> int | None:
    header = response.headers.get("Retry-After")
    if not header:
        return None
    try:
        return max(1, int(float(header)))
    except ValueError:
        return None


def _http_error(response: httpx.Response) -> ProviderError:
    snippet = _safe_error_snippet(response)
    status = response.status_code
    logger.warning("LLM provider HTTP status=%s", status)
    if status in (401, 403):
        return ProviderError(
            "LLM provider rejected credentials",
            code="invalid_credentials",
            status_code=502,
            detail=snippet,
        )
    if status == 429:
        return ProviderError(
            "The AI provider has reached its request limit. Please wait before trying again.",
            code="rate_limited",
            status_code=429,
            detail=snippet,
            retry_after=_parse_retry_after_seconds(response),
        )
    if status == 404:
        return ProviderError(
            "The configured LLM model is not available",
            code="unsupported_model",
            status_code=502,
            detail=snippet,
        )
    if status == 400:
        return ProviderError(
            "LLM provider rejected the request",
            code="invalid_request",
            status_code=502,
            detail=snippet,
        )
    if status == 503:
        return ProviderError(
            "The AI provider is temporarily unavailable. "
            "Your match context is preserved. Please try again later.",
            code="provider_unavailable",
            status_code=503,
            detail=snippet,
        )
    if status in {500, 502, 504}:
        return ProviderError(
            "The AI provider is temporarily unavailable. "
            "Your match context is preserved. Please try again later.",
            code="provider_error",
            status_code=502,
            detail=snippet,
        )
    return ProviderError(
        "LLM provider request failed",
        code="provider_error",
        status_code=502,
        detail=snippet,
    )


def _safe_error_snippet(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    message: object = None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("status")
        elif isinstance(error, str):
            message = error
        else:
            message = body.get("message")
    if not isinstance(message, str):
        return None
    cleaned = _SECRET_RE.sub(r"\1\2[redacted]", message).strip()
    if not cleaned:
        return None
    return cleaned[:240]


def _backoff(attempt: int) -> float:
    base = min(0.25 * (2**attempt), 2.0)
    return min(base * (0.5 + random.random()), 2.0)


def _retry_after(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return min(float(header), 5.0)
        except ValueError:
            pass
    return _backoff(attempt)
