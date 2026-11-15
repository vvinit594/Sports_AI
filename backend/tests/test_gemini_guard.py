"""Phase 1 Gemini free-tier protection: RPM, daily budget, queue, cache, retries."""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import ProviderError
from app.main import create_app
from app.schemas.explanation import AudienceLevel, ExplanationResponse
from app.services.api.catalog import MatchCatalog
from app.services.explanations.cache import (
    ExplanationResponseCache,
    explanation_cache_key,
)
from app.services.explanations.guard import ConcurrencyGate, GeminiRequestManager
from app.services.explanations.providers.gemini import GeminiProvider
from app.services.explanations.providers.http import JsonHttpClient
from app.services.explanations.usage import InMemoryGeminiUsageStore
from tests.api_helpers import heuristic_artifact, sample_chase_match


def _payload() -> dict[str, object]:
    return {
        "summary": "A short summary",
        "what_happened": "A ball was bowled",
        "why_it_matters": "It changes the chase",
        "match_context": "Beta are chasing",
        "key_factors": ["score is 10 for 1"],
    }


def _gemini_body(text: str | None = None) -> dict[str, object]:
    return {
        "candidates": [
            {"content": {"parts": [{"text": text or json.dumps(_payload())}]}}
        ]
    }


def _settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {
        "environment": "test",
        "log_level": "WARNING",
        "llm_provider": "gemini",
        "llm_model": "gemini-3.8-flash",
        "gemini_api_key": "test-key",
        "llm_timeout_seconds": 2.0,
        "llm_request_deadline_seconds": 3.0,
        "gemini_max_retries": 0,
        "gemini_max_requests_per_minute": 4,
        "gemini_daily_request_budget": 12,
        "gemini_max_concurrent_requests": 1,
        "gemini_queue_wait_seconds": 0,
        "gemini_cache_ttl_seconds": 3600,
    }
    payload.update(overrides)
    return Settings.model_validate(payload)


def _gemini_client(
    handler,
    *,
    settings: Settings | None = None,
    max_retries: int | None = None,
    match_id: str = "g-1",
):
    resolved = settings or _settings()
    retries = resolved.gemini_max_retries if max_retries is None else max_retries
    match, states = sample_chase_match(match_id)
    provider = GeminiProvider(
        api_key="test-key",
        model_name="gemini-3.8-flash",
        base_url="https://example.test/gemini",
        timeout_seconds=resolved.llm_timeout_seconds,
        max_retries=retries,
        request_deadline_seconds=resolved.llm_request_deadline_seconds,
        client=JsonHttpClient(
            timeout_seconds=resolved.llm_timeout_seconds,
            max_retries=retries,
            request_deadline_seconds=resolved.llm_request_deadline_seconds,
            transport=httpx.MockTransport(handler),
        ),
    )
    app = create_app(
        resolved,
        catalog=MatchCatalog.from_matches([match]),
        model_artifact=heuristic_artifact(),
        llm_provider=provider,
    )
    from fastapi.testclient import TestClient

    return TestClient(app), states, app


def test_rpm_allows_four_then_rejects_fifth():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_gemini_body())

    client, states, _app = _gemini_client(
        handler, settings=_settings(gemini_cache_ttl_seconds=0)
    )
    latest = states[-1].sequence
    for index in range(4):
        response = client.post(
            "/api/v1/matches/g-1/explanations",
            json={"audience_level": "beginner", "sequence": latest - index},
        )
        assert response.status_code == 200, response.text
    fifth = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "casual", "sequence": latest},
    )
    assert fifth.status_code == 429
    body = fifth.json()
    assert body["code"] == "application_rate_limited"
    assert "several AI requests" in body["error"]
    assert fifth.headers.get("retry-after")
    assert int(fifth.headers["retry-after"]) >= 1
    assert calls["count"] == 4


def test_rpm_allows_request_after_window_expires():
    store = InMemoryGeminiUsageStore()
    clock = {"now": 1000.0}
    manager = GeminiRequestManager(
        rpm_limit=1,
        daily_budget=10,
        max_concurrent=1,
        cache_ttl_seconds=0,
        store=store,
        monotonic=lambda: clock["now"],
        utc_now=lambda: datetime(2026, 11, 15, 12, 0, tzinfo=UTC),
    )
    manager.reserve_outbound()
    with pytest.raises(ProviderError) as blocked:
        manager.reserve_outbound()
    assert blocked.value.code == "application_rate_limited"
    clock["now"] = 1061.0
    manager.reserve_outbound()


def test_rpm_retry_after_matches_oldest_entry():
    store = InMemoryGeminiUsageStore()
    manager = GeminiRequestManager(
        rpm_limit=1,
        daily_budget=10,
        max_concurrent=1,
        cache_ttl_seconds=0,
        store=store,
        monotonic=lambda: 10.0,
        utc_now=lambda: datetime(2026, 11, 15, 12, 0, tzinfo=UTC),
    )
    manager.reserve_outbound()
    with pytest.raises(ProviderError) as exc:
        manager.reserve_outbound()
    assert exc.value.retry_after == 60


def test_concurrent_rpm_reservations_cannot_exceed_limit():
    manager = GeminiRequestManager(
        rpm_limit=4,
        daily_budget=50,
        max_concurrent=8,
        cache_ttl_seconds=0,
    )
    errors: list[str] = []

    def worker() -> None:
        try:
            manager.reserve_outbound()
        except ProviderError as exc:
            errors.append(exc.code)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    snapshot = manager.snapshot()
    assert snapshot.requests_in_current_minute == 4
    assert errors.count("application_rate_limited") == 8


def test_retries_consume_rpm_capacity():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": "rate"})
        return httpx.Response(200, json=_gemini_body())

    client, states, app = _gemini_client(
        handler,
        settings=_settings(
            gemini_max_retries=1,
            gemini_max_requests_per_minute=1,
            gemini_daily_request_budget=12,
            gemini_cache_ttl_seconds=0,
        ),
        max_retries=1,
    )
    latest = states[-1].sequence
    first = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert first.status_code == 429
    assert first.json()["code"] == "application_rate_limited"
    assert calls["count"] == 1
    assert app.state.gemini_guard.snapshot().requests_in_current_minute == 1


def test_daily_budget_rejects_after_exhaustion():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_gemini_body())

    client, states, _app = _gemini_client(
        handler,
        settings=_settings(
            gemini_daily_request_budget=2,
            gemini_max_requests_per_minute=4,
            gemini_cache_ttl_seconds=0,
        ),
    )
    latest = states[-1].sequence
    for audience in ("beginner", "casual"):
        response = client.post(
            "/api/v1/matches/g-1/explanations",
            json={"audience_level": audience, "sequence": latest},
        )
        assert response.status_code == 200
    blocked = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "advanced", "sequence": latest},
    )
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["code"] == "daily_budget_exhausted"
    assert "allowance for today" in body["error"]
    assert blocked.headers.get("retry-after")
    assert calls["count"] == 2


def test_daily_budget_resets_on_utc_day_change():
    store = InMemoryGeminiUsageStore()
    clock = {"now": datetime(2026, 11, 15, 23, 59, tzinfo=UTC)}
    manager = GeminiRequestManager(
        rpm_limit=10,
        daily_budget=1,
        max_concurrent=1,
        cache_ttl_seconds=0,
        store=store,
        utc_now=lambda: clock["now"],
    )
    manager.reserve_outbound()
    with pytest.raises(ProviderError) as blocked:
        manager.reserve_outbound()
    assert blocked.value.code == "daily_budget_exhausted"
    clock["now"] = datetime(2026, 11, 16, 0, 0, 1, tzinfo=UTC)
    manager.reserve_outbound()


def test_concurrent_daily_reservations_cannot_overspend():
    manager = GeminiRequestManager(
        rpm_limit=50,
        daily_budget=3,
        max_concurrent=8,
        cache_ttl_seconds=0,
    )
    codes: list[str] = []

    def worker() -> None:
        try:
            manager.reserve_outbound()
            codes.append("ok")
        except ProviderError as exc:
            codes.append(exc.code)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert codes.count("ok") == 3
    assert codes.count("daily_budget_exhausted") == 7
    assert manager.snapshot().daily_requests_used == 3
    assert manager.snapshot().resets_on_process_restart is True
    assert manager.snapshot().storage == "process_local"


def test_process_local_store_starts_empty():
    first = InMemoryGeminiUsageStore()
    second = InMemoryGeminiUsageStore()
    now = datetime(2026, 11, 15, tzinfo=UTC)
    first.reserve_attempt(1.0, now, rpm_limit=4, window_seconds=60, daily_budget=12)
    snap = second.snapshot(
        1.0,
        now,
        rpm_limit=4,
        window_seconds=60,
        daily_budget=12,
        max_concurrent_requests=1,
        cache_entries=0,
        cache_ttl_seconds=3600,
    )
    assert snap.daily_requests_used == 0
    assert snap.requests_in_current_minute == 0


def test_only_one_gemini_request_active_at_a_time():
    active = {"count": 0, "max": 0}
    lock = threading.Lock()
    released = threading.Event()

    def handler(_request: httpx.Request) -> httpx.Response:
        with lock:
            active["count"] += 1
            active["max"] = max(active["max"], active["count"])
        released.wait(timeout=1)
        with lock:
            active["count"] -= 1
        return httpx.Response(200, json=_gemini_body())

    _client, states, app = _gemini_client(
        handler,
        settings=_settings(
            gemini_cache_ttl_seconds=0,
            gemini_max_concurrent_requests=1,
            gemini_queue_wait_seconds=0,
            gemini_max_requests_per_minute=10,
        ),
    )
    latest = states[-1].sequence
    service = app.state.explanations
    results: list[str] = []

    def run(audience: str) -> None:
        try:
            service.explain("g-1", AudienceLevel(audience), latest)
            results.append("ok")
        except ProviderError as exc:
            results.append(exc.code)

    first = threading.Thread(target=run, args=("beginner",))
    first.start()
    time.sleep(0.05)
    second = threading.Thread(target=run, args=("casual",))
    second.start()
    time.sleep(0.05)
    released.set()
    first.join(timeout=2)
    second.join(timeout=2)
    assert "ok" in results
    assert "application_rate_limited" in results
    assert active["max"] == 1


def test_concurrency_gate_releases_after_failure_and_does_not_deadlock():
    gate = ConcurrencyGate(max_concurrent=1, wait_seconds=0)
    with pytest.raises(RuntimeError):
        with gate:
            raise RuntimeError("boom")
    with gate:
        pass
    with pytest.raises(ProviderError) as exc:
        with gate:
            with gate:
                pass
    assert exc.value.code == "application_rate_limited"


def test_provider_failure_releases_concurrency_slot():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(200, json=_gemini_body())

    client, states, _app = _gemini_client(
        handler, settings=_settings(gemini_cache_ttl_seconds=0)
    )
    latest = states[-1].sequence
    first = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert first.status_code == 503
    assert first.json()["code"] == "provider_unavailable"
    second = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "casual", "sequence": latest},
    )
    assert second.status_code == 200
    assert calls["count"] == 2


def test_repeated_failures_do_not_deadlock_the_queue():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    client, states, _app = _gemini_client(
        handler, settings=_settings(gemini_cache_ttl_seconds=0)
    )
    latest = states[-1].sequence
    for _ in range(4):
        response = client.post(
            "/api/v1/matches/g-1/explanations",
            json={"audience_level": "beginner", "sequence": latest},
        )
        assert response.status_code == 502
        assert response.json()["code"] == "provider_error"


def test_status_codes_make_one_outbound_attempt_only():
    cases = {
        400: "invalid_request",
        401: "invalid_credentials",
        403: "invalid_credentials",
        404: "unsupported_model",
        429: "rate_limited",
        500: "provider_error",
        502: "provider_error",
        503: "provider_unavailable",
        504: "provider_error",
    }
    for status, code in cases.items():
        calls = {"count": 0}

        def handler(
            _request: httpx.Request,
            status=status,
            calls=calls,
        ) -> httpx.Response:
            calls["count"] += 1
            headers = {"Retry-After": "7"} if status == 429 else None
            return httpx.Response(status, json={"error": "x"}, headers=headers)

        client, states, _app = _gemini_client(
            handler,
            settings=_settings(
                gemini_cache_ttl_seconds=0, gemini_daily_request_budget=12
            ),
            match_id=f"one-{status}",
        )
        response = client.post(
            f"/api/v1/matches/one-{status}/explanations",
            json={"audience_level": "beginner", "sequence": states[-1].sequence},
        )
        assert calls["count"] == 1, status
        assert response.json()["code"] == code, status
        if status == 429:
            assert response.status_code == 429
            assert response.headers.get("retry-after") == "7"
            assert "Gemini has reached its request limit" in response.json()["error"]
        if status == 503:
            assert "rate" not in response.json()["error"].lower()


def test_timeout_makes_one_outbound_attempt_only():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.TimeoutException("slow", request=request)

    client, states, _app = _gemini_client(
        handler, settings=_settings(gemini_cache_ttl_seconds=0)
    )
    response = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": states[-1].sequence},
    )
    assert response.status_code == 504
    assert response.json()["code"] == "timeout"
    assert "could not finish this explanation in time" in response.json()["error"]
    assert calls["count"] == 1


def test_cache_hit_does_not_call_gemini_again():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_gemini_body())

    client, states, _app = _gemini_client(handler)
    latest = states[-1].sequence
    first = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    second = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["summary"] == second.json()["summary"]
    assert calls["count"] == 1


def test_cache_key_changes_with_sequence_and_audience():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_gemini_body())

    client, states, _app = _gemini_client(handler)
    latest = states[-1].sequence
    client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest - 1},
    )
    client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "advanced", "sequence": latest},
    )
    assert calls["count"] == 3
    beginner = explanation_cache_key(
        match_id="g-1",
        sequence=latest,
        audience_level=AudienceLevel.BEGINNER,
        model_id="test_heuristic",
    )
    other_seq = explanation_cache_key(
        match_id="g-1",
        sequence=latest - 1,
        audience_level=AudienceLevel.BEGINNER,
        model_id="test_heuristic",
    )
    advanced = explanation_cache_key(
        match_id="g-1",
        sequence=latest,
        audience_level=AudienceLevel.ADVANCED,
        model_id="test_heuristic",
    )
    assert len({beginner, other_seq, advanced}) == 3


def test_failed_responses_are_not_cached():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(200, json=_gemini_body())

    client, states, _app = _gemini_client(handler)
    latest = states[-1].sequence
    first = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    second = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert first.status_code == 503
    assert second.status_code == 200
    assert calls["count"] == 2


def test_expired_cache_entries_are_removed():
    clock = {"now": 1.0}
    cache = ExplanationResponseCache(
        ttl_seconds=10, max_entries=8, monotonic=lambda: clock["now"]
    )
    response = ExplanationResponse.model_validate(
        {
            "summary": "s",
            "what_happened": "h",
            "why_it_matters": "w",
            "match_context": "c",
            "key_factors": ["k"],
            "audience_level": "beginner",
            "source_match_id": "g-1",
            "source_sequence": 1,
            "generated_at": "2026-11-15T00:00:00Z",
            "model_provider": "gemini",
            "model_name": "gemini-3.8-flash",
        }
    )
    cache.put("k1", response)
    assert cache.get("k1") is not None
    clock["now"] = 12.0
    assert cache.get("k1") is None
    assert cache.size() == 0


def test_cache_size_remains_bounded():
    cache = ExplanationResponseCache(
        ttl_seconds=60, max_entries=3, monotonic=time.monotonic
    )
    response = ExplanationResponse.model_validate(
        {
            "summary": "s",
            "what_happened": "h",
            "why_it_matters": "w",
            "match_context": "c",
            "key_factors": ["k"],
            "audience_level": "beginner",
            "source_match_id": "g-1",
            "source_sequence": 1,
            "generated_at": "2026-11-15T00:00:00Z",
            "model_provider": "gemini",
            "model_name": "gemini-3.8-flash",
        }
    )
    for index in range(10):
        cache.put(f"k{index}", response)
    assert cache.size() == 3


def test_simultaneous_identical_requests_share_one_provider_call():
    calls = {"count": 0}
    hold = threading.Event()
    entered = threading.Event()

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        entered.set()
        hold.wait(timeout=1)
        return httpx.Response(200, json=_gemini_body())

    _client, states, app = _gemini_client(
        handler,
        settings=_settings(gemini_max_requests_per_minute=10),
    )
    latest = states[-1].sequence
    service = app.state.explanations
    results: list[str] = []
    errors: list[str] = []

    def run() -> None:
        try:
            service.explain("g-1", AudienceLevel.BEGINNER, latest)
            results.append("ok")
        except Exception as exc:
            errors.append(type(exc).__name__)

    workers = [threading.Thread(target=run) for _ in range(3)]
    for worker in workers:
        worker.start()
    assert entered.wait(timeout=1)
    hold.set()
    for worker in workers:
        worker.join(timeout=2)
    assert errors == []
    assert results == ["ok", "ok", "ok"]
    assert calls["count"] == 1


def test_readiness_exposes_process_local_usage_without_secrets():
    client, _states, _app = _gemini_client(
        lambda _request: httpx.Response(200, json=_gemini_body())
    )
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["llm_provider"] == "gemini"
    assert body["llm_model"] == "gemini-3.8-flash"
    usage = body["llm_usage"]
    assert usage["storage"] == "process_local"
    assert usage["resets_on_process_restart"] is True
    assert usage["max_requests_per_minute"] == 4
    assert usage["daily_request_budget"] == 12
    assert "test-key" not in response.text
    assert "GEMINI_API_KEY" not in response.text


def test_mock_provider_is_not_rate_limited():
    from tests.api_helpers import api_client

    match, _ = sample_chase_match("mock-limit")
    client = api_client(matches=[match])
    for _ in range(6):
        response = client.post(
            "/api/v1/matches/mock-limit/explanations",
            json={"audience_level": "beginner"},
        )
        assert response.status_code == 200


def test_health_and_match_routes_still_work_with_gemini_guard():
    client, states, _app = _gemini_client(
        lambda _request: httpx.Response(200, json=_gemini_body())
    )
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health/ready").status_code == 200
    assert client.get("/api/v1/matches").status_code == 200
    assert client.get("/api/v1/matches/g-1").status_code == 200
    assert client.get("/api/v1/matches/g-1/state").status_code == 200
    assert client.get("/api/v1/matches/g-1/win-probability").status_code == 200
    assert client.get("/api/v1/matches/g-1/moments").status_code == 200
    explained = client.post(
        "/api/v1/matches/g-1/explanations",
        json={"audience_level": "beginner", "sequence": states[-1].sequence},
    )
    assert explained.status_code == 200
    assert explained.json()["audience_level"] == "beginner"
    assert "summary" in explained.json()
