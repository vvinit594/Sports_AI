"""Replaceable Gemini usage counters.

Phase 1 uses a process-local in-memory store. There is no database or Redis
in this deployment, so the counters reset on process restart and are not
shared across Render instances or other apps on the same Google project.

This does not enforce Google's Free Tier quota. It only limits this process.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Protocol


@dataclass(frozen=True)
class UsageSnapshot:
    storage: str
    max_requests_per_minute: int
    requests_in_current_minute: int
    daily_request_budget: int
    daily_requests_used: int
    daily_resets_at_utc: str
    max_concurrent_requests: int
    cache_entries: int
    cache_ttl_seconds: int
    resets_on_process_restart: bool = True


class GeminiUsageStore(Protocol):
    """Storage seam for later shared counters. Phase 1 is process-local."""

    def reserve_attempt(
        self,
        now: float,
        now_utc: datetime,
        *,
        rpm_limit: int,
        window_seconds: float,
        daily_budget: int,
    ) -> tuple[str | None, float | None]:
        """Reserve RPM and daily slots together.

        Returns ``(None, None)`` on success, or ``(reason, retry_after)`` where
        reason is ``daily`` or ``rpm``.
        """

    def snapshot(
        self,
        now: float,
        now_utc: datetime,
        *,
        rpm_limit: int,
        window_seconds: float,
        daily_budget: int,
        max_concurrent_requests: int,
        cache_entries: int,
        cache_ttl_seconds: int,
    ) -> UsageSnapshot: ...


class InMemoryGeminiUsageStore:
    """Thread-safe process-local RPM and UTC-day counters."""

    storage_name = "process_local"

    def __init__(self) -> None:
        self._lock = Lock()
        self._rpm_times: deque[float] = deque()
        self._day: str | None = None
        self._daily_count = 0

    def reserve_attempt(
        self,
        now: float,
        now_utc: datetime,
        *,
        rpm_limit: int,
        window_seconds: float,
        daily_budget: int,
    ) -> tuple[str | None, float | None]:
        current = _utc(now_utc)
        day_key = current.date().isoformat()
        with self._lock:
            if self._day != day_key:
                self._day = day_key
                self._daily_count = 0
            if self._daily_count >= daily_budget:
                return "daily", float(seconds_until_next_utc_midnight(current))
            self._evict_rpm(now, window_seconds)
            if len(self._rpm_times) >= rpm_limit:
                oldest = self._rpm_times[0]
                return "rpm", max(1.0, oldest + window_seconds - now)
            self._daily_count += 1
            self._rpm_times.append(now)
            return None, None

    def snapshot(
        self,
        now: float,
        now_utc: datetime,
        *,
        rpm_limit: int,
        window_seconds: float,
        daily_budget: int,
        max_concurrent_requests: int,
        cache_entries: int,
        cache_ttl_seconds: int,
    ) -> UsageSnapshot:
        current = _utc(now_utc)
        day_key = current.date().isoformat()
        with self._lock:
            self._evict_rpm(now, window_seconds)
            daily_used = self._daily_count if self._day == day_key else 0
            rpm_used = len(self._rpm_times)
        reset_at = datetime.combine(
            current.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=UTC,
        )
        return UsageSnapshot(
            storage=self.storage_name,
            max_requests_per_minute=rpm_limit,
            requests_in_current_minute=rpm_used,
            daily_request_budget=daily_budget,
            daily_requests_used=daily_used,
            daily_resets_at_utc=reset_at.isoformat().replace("+00:00", "Z"),
            max_concurrent_requests=max_concurrent_requests,
            cache_entries=cache_entries,
            cache_ttl_seconds=cache_ttl_seconds,
            resets_on_process_restart=True,
        )

    def _evict_rpm(self, now: float, window_seconds: float) -> None:
        cutoff = now - window_seconds
        while self._rpm_times and self._rpm_times[0] <= cutoff:
            self._rpm_times.popleft()


def seconds_until_next_utc_midnight(now: datetime) -> int:
    current = _utc(now)
    tomorrow = datetime.combine(
        current.date() + timedelta(days=1),
        datetime.min.time(),
        tzinfo=UTC,
    )
    return max(1, int((tomorrow - current).total_seconds()))


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
