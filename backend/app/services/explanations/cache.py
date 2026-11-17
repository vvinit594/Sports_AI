"""Bounded TTL cache and in-flight coalescing for Gemini explanations.

There is no user authentication. Successful explanations for identical
historical match contexts are shared across callers of this process. The cache
key is derived only from match identity, sequence, audience, and model id.
API keys and prompts are never stored as keys.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from collections.abc import Callable
from threading import Event, Lock
from typing import TypeVar

from app.schemas.explanation import AudienceLevel, ExplanationResponse

T = TypeVar("T")
_DEFAULT_MAX_ENTRIES = 256


def explanation_cache_key(
    *,
    match_id: str,
    sequence: int,
    audience_level: AudienceLevel | str,
    model_id: str | None,
    question: str | None = None,
) -> str:
    payload = {
        "audience_level": str(audience_level),
        "data_source": "historical_cricsheet",
        "match_id": match_id,
        "model_id": model_id or "",
        "sequence": sequence,
    }
    cleaned = (question or "").strip().lower()
    if cleaned:
        payload["question"] = cleaned
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _SharedCall:
    def __init__(self) -> None:
        self._event = Event()
        self._result: object | None = None
        self._error: BaseException | None = None

    def succeed(self, result: object) -> None:
        self._result = result
        self._event.set()

    def fail(self, error: BaseException) -> None:
        self._error = error
        self._event.set()

    def wait(self) -> object:
        self._event.wait()
        if self._error is not None:
            raise self._error
        return self._result


class ExplanationResponseCache:
    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
        monotonic: Callable[[], float],
    ):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max(1, max_entries)
        self._monotonic = monotonic
        self._lock = Lock()
        self._entries: OrderedDict[str, tuple[float, ExplanationResponse]] = (
            OrderedDict()
        )
        self._inflight: dict[str, _SharedCall] = {}

    def get(self, key: str) -> ExplanationResponse | None:
        if self.ttl_seconds <= 0:
            return None
        now = self._monotonic()
        with self._lock:
            self._evict_expired(now)
            item = self._entries.get(key)
            if item is None:
                return None
            expires_at, response = item
            if expires_at <= now:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return response

    def put(self, key: str, response: ExplanationResponse) -> None:
        if self.ttl_seconds <= 0:
            return
        now = self._monotonic()
        expires_at = now + self.ttl_seconds
        with self._lock:
            self._evict_expired(now)
            self._entries[key] = (expires_at, response)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def coalesce(self, key: str, producer: Callable[[], T]) -> T:
        """Share one in-flight producer across identical concurrent requests."""

        with self._lock:
            existing = self._inflight.get(key)
            if existing is not None:
                shared = existing
                waiter = True
            else:
                shared = _SharedCall()
                self._inflight[key] = shared
                waiter = False
        if waiter:
            return shared.wait()  # type: ignore[return-value]
        try:
            result = producer()
            shared.succeed(result)
            return result
        except BaseException as exc:
            shared.fail(exc)
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)

    def size(self) -> int:
        now = self._monotonic()
        with self._lock:
            self._evict_expired(now)
            return len(self._entries)

    def _evict_expired(self, now: float) -> None:
        expired = [
            key for key, (expires_at, _) in self._entries.items() if expires_at <= now
        ]
        for key in expired:
            self._entries.pop(key, None)
