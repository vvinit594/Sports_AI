"""Shared Gemini free-tier guard: RPM, daily budget, and single-flight queue.

The limiter is process-local and initialized once in the FastAPI app factory.
FastAPI runs the synchronous explanation route in a worker thread, so this
module uses threading primitives. That keeps the event loop free during the
blocking Gemini HTTP call without adding a second HTTP client.

Retries, if enabled, must call ``reserve_outbound`` once per attempt.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from threading import BoundedSemaphore, Lock
from typing import TypeVar

from app.core.config import Settings
from app.core.exceptions import ProviderError
from app.core.logging import log_event
from app.services.explanations.cache import ExplanationResponseCache
from app.services.explanations.usage import (
    GeminiUsageStore,
    InMemoryGeminiUsageStore,
    UsageSnapshot,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

APPLICATION_RPM_MESSAGE = (
    "PulseIQ is handling several AI requests right now. Please try again shortly."
)
DAILY_BUDGET_MESSAGE = (
    "PulseIQ has reached its AI request allowance for today. "
    "Cricket match information remains available."
)
QUEUE_BUSY_MESSAGE = APPLICATION_RPM_MESSAGE


class ConcurrencyGate:
    """At most N Gemini provider calls at a time. Rejects instead of queueing."""

    def __init__(self, *, max_concurrent: int, wait_seconds: float):
        self.max_concurrent = max(1, max_concurrent)
        self.wait_seconds = max(0.0, wait_seconds)
        self._semaphore = BoundedSemaphore(self.max_concurrent)

    def acquire(self) -> None:
        timeout = self.wait_seconds
        log_event(
            logger,
            "gemini_queue_wait",
            max_concurrent=self.max_concurrent,
            wait_seconds=timeout,
        )
        acquired = self._semaphore.acquire(timeout=timeout if timeout > 0 else 0)
        if not acquired:
            retry_after = max(1, int(timeout) if timeout > 0 else 1)
            log_event(
                logger,
                "gemini_queue_rejected",
                max_concurrent=self.max_concurrent,
                retry_after=retry_after,
            )
            raise ProviderError(
                QUEUE_BUSY_MESSAGE,
                code="application_rate_limited",
                status_code=429,
                retry_after=retry_after,
            )

    def release(self) -> None:
        self._semaphore.release()

    def __enter__(self) -> ConcurrencyGate:
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.release()


class GeminiRequestManager:
    """Single shared guard for every Gemini generateContent attempt."""

    def __init__(
        self,
        *,
        rpm_limit: int,
        daily_budget: int,
        max_concurrent: int,
        cache_ttl_seconds: float,
        queue_wait_seconds: float = 0.0,
        window_seconds: float = 60.0,
        store: GeminiUsageStore | None = None,
        monotonic: Callable[[], float] | None = None,
        utc_now: Callable[[], datetime] | None = None,
        cache_max_entries: int = 256,
    ):
        self.rpm_limit = max(1, rpm_limit)
        self.daily_budget = max(0, daily_budget)
        self.window_seconds = window_seconds
        self.store = store or InMemoryGeminiUsageStore()
        self._monotonic = monotonic or time.monotonic
        self._utc_now = utc_now or (lambda: datetime.now(UTC))
        self.cache = ExplanationResponseCache(
            ttl_seconds=cache_ttl_seconds,
            max_entries=cache_max_entries,
            monotonic=self._monotonic,
        )
        self.gate = ConcurrencyGate(
            max_concurrent=max_concurrent,
            wait_seconds=queue_wait_seconds,
        )
        self._hook_lock = Lock()

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        store: GeminiUsageStore | None = None,
    ) -> GeminiRequestManager:
        return cls(
            rpm_limit=settings.gemini_max_requests_per_minute,
            daily_budget=settings.gemini_daily_request_budget,
            max_concurrent=settings.gemini_max_concurrent_requests,
            cache_ttl_seconds=settings.gemini_cache_ttl_seconds,
            queue_wait_seconds=settings.gemini_queue_wait_seconds,
            store=store,
        )

    def reserve_outbound(self) -> None:
        """Count one actual Gemini HTTP attempt. Raises 429 when local limits hit."""

        reason, retry = self.store.reserve_attempt(
            self._monotonic(),
            self._utc_now(),
            rpm_limit=self.rpm_limit,
            window_seconds=self.window_seconds,
            daily_budget=self.daily_budget,
        )
        if reason == "daily":
            retry_after = max(1, int(retry or 1))
            log_event(
                logger,
                "gemini_daily_budget_rejected",
                daily_budget=self.daily_budget,
                retry_after=retry_after,
            )
            raise ProviderError(
                DAILY_BUDGET_MESSAGE,
                code="daily_budget_exhausted",
                status_code=429,
                retry_after=retry_after,
            )
        if reason == "rpm":
            retry_after = max(1, int(retry or 1))
            log_event(
                logger,
                "gemini_rpm_rejected",
                rpm_limit=self.rpm_limit,
                retry_after=retry_after,
            )
            raise ProviderError(
                APPLICATION_RPM_MESSAGE,
                code="application_rate_limited",
                status_code=429,
                retry_after=retry_after,
            )
        log_event(
            logger,
            "gemini_request_accepted",
            rpm_limit=self.rpm_limit,
            daily_budget=self.daily_budget,
        )

    def bind_http_client(self, client: object) -> None:
        """Count every JsonHttpClient attempt, including explicit retries."""

        with self._hook_lock:
            client.attempt_hook = self.reserve_outbound  # type: ignore[attr-defined]

    def snapshot(self) -> UsageSnapshot:
        return self.store.snapshot(
            self._monotonic(),
            self._utc_now(),
            rpm_limit=self.rpm_limit,
            window_seconds=self.window_seconds,
            daily_budget=self.daily_budget,
            max_concurrent_requests=self.gate.max_concurrent,
            cache_entries=self.cache.size(),
            cache_ttl_seconds=int(self.cache.ttl_seconds),
        )
