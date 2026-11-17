"""Bounded TTL cache and in-flight coalescing for Gemini explanations.

There is no user authentication. Successful explanations for identical
historical match contexts are shared across callers of this process.

Cache keys isolate match id, sequence, audience, cricket model id, LLM
provider/model, and a conservatively normalized question. API keys and full
prompts are never stored as keys. Failures are never cached.

TTL defaults to GEMINI_CACHE_TTL_SECONDS (3600). Eviction is LRU when the
bounded entry limit is exceeded. Counters are process-local.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event, Lock
from typing import TypeVar

from app.schemas.explanation import AudienceLevel, ExplanationResponse

T = TypeVar("T")
_DEFAULT_MAX_ENTRIES = 256
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class CacheStats:
    hits: int = 0
    misses: int = 0
    coalesce_hits: int = 0
    expirations: int = 0
    lru_evictions: int = 0
    entries: int = 0
    max_entries: int = _DEFAULT_MAX_ENTRIES
    ttl_seconds: float = 0.0


def normalize_cache_question(question: str | None) -> str:
    """Conservative key normalization: trim, collapse whitespace, lowercase.

    Does not expand contractions or strip words. Meaning-bearing tokens stay.
    """

    if question is None:
        return ""
    return _WHITESPACE_RE.sub(" ", question.strip().lower())


def explanation_cache_key(
    *,
    match_id: str,
    sequence: int,
    audience_level: AudienceLevel | str,
    model_id: str | None,
    question: str | None = None,
    provider_name: str | None = None,
    llm_model: str | None = None,
) -> str:
    payload = {
        "audience_level": str(audience_level),
        "data_source": "historical_cricsheet",
        "llm_model": (llm_model or "").strip(),
        "match_id": match_id,
        "model_id": model_id or "",
        "provider_name": (provider_name or "").strip(),
        "sequence": sequence,
    }
    cleaned = normalize_cache_question(question)
    if cleaned:
        payload["question"] = cleaned
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_cacheable_explanation(response: ExplanationResponse) -> bool:
    """Only complete successful Gemini explanations may enter the cache."""

    required = (
        response.summary,
        response.what_happened,
        response.why_it_matters,
        response.match_context,
    )
    if any(not isinstance(item, str) or not item.strip() for item in required):
        return False
    if not response.grounded:
        return False
    if response.degraded:
        return False
    if response.explanation_source != "gemini":
        return False
    if response.fallback_reason:
        return False
    return True


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
        self._hits = 0
        self._misses = 0
        self._coalesce_hits = 0
        self._expirations = 0
        self._lru_evictions = 0

    def get(self, key: str) -> ExplanationResponse | None:
        if self.ttl_seconds <= 0:
            with self._lock:
                self._misses += 1
            return None
        now = self._monotonic()
        with self._lock:
            self._evict_expired(now)
            item = self._entries.get(key)
            if item is None:
                self._misses += 1
                return None
            expires_at, response = item
            if expires_at <= now:
                self._entries.pop(key, None)
                self._expirations += 1
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return response

    def put(self, key: str, response: ExplanationResponse) -> bool:
        if self.ttl_seconds <= 0:
            return False
        if not is_cacheable_explanation(response):
            return False
        now = self._monotonic()
        expires_at = now + self.ttl_seconds
        with self._lock:
            self._evict_expired(now)
            self._entries[key] = (expires_at, response)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
                self._lru_evictions += 1
        return True

    def coalesce(self, key: str, producer: Callable[[], T]) -> T:
        """Share one in-flight producer across identical concurrent requests."""

        with self._lock:
            existing = self._inflight.get(key)
            if existing is not None:
                shared = existing
                waiter = True
                self._coalesce_hits += 1
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

    def stats(self) -> CacheStats:
        now = self._monotonic()
        with self._lock:
            self._evict_expired(now)
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                coalesce_hits=self._coalesce_hits,
                expirations=self._expirations,
                lru_evictions=self._lru_evictions,
                entries=len(self._entries),
                max_entries=self.max_entries,
                ttl_seconds=self.ttl_seconds,
            )

    def _evict_expired(self, now: float) -> None:
        expired = [
            key for key, (expires_at, _) in self._entries.items() if expires_at <= now
        ]
        for key in expired:
            self._entries.pop(key, None)
            self._expirations += 1
