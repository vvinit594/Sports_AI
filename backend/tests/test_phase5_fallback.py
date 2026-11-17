"""Phase 5: graceful degradation, fallback source, and cache isolation."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.exceptions import ProviderError
from app.main import create_app
from app.schemas.explanation import AudienceLevel, ExplanationResponse
from app.services.api.catalog import MatchCatalog
from app.services.explanations.cache import (
    ExplanationResponseCache,
    is_cacheable_explanation,
)
from app.services.explanations.fallback import (
    build_verified_facts_fallback,
    fallback_reason_for,
    is_fallback_eligible,
)
from app.services.explanations.providers.gemini import GeminiProvider
from app.services.explanations.providers.http import JsonHttpClient
from app.services.explanations.service import ExplanationService
from tests.api_helpers import (
    ScriptedProvider,
    empty_context,
    heuristic_artifact,
    sample_chase_match,
)
from tests.api_helpers import test_settings as settings_for_tests


def _gemini_body() -> dict[str, object]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "summary": "Gemini summary",
                                    "what_happened": "A delivery",
                                    "why_it_matters": "Chase pressure",
                                    "match_context": "Beta chase",
                                    "key_factors": ["score"],
                                }
                            )
                        }
                    ]
                },
                "finishReason": "STOP",
            }
        ]
    }


def _gemini_client(handler, *, match_id: str = "p5-1", **setting_overrides):
    match, states = sample_chase_match(match_id)
    payload = {
        "llm_provider": "gemini",
        "gemini_api_key": "test-key",
        "llm_model": "gemini-3.8-flash",
        "gemini_max_retries": 0,
        "gemini_max_requests_per_minute": 4,
        "gemini_daily_request_budget": 12,
        "gemini_cache_ttl_seconds": 3600,
        "gemini_max_concurrent_requests": 1,
        "gemini_queue_wait_seconds": 0,
        "llm_timeout_seconds": 2.0,
        "llm_request_deadline_seconds": 3.0,
    }
    payload.update(setting_overrides)
    settings = settings_for_tests(**payload)
    provider = GeminiProvider(
        api_key="test-key",
        model_name="gemini-3.8-flash",
        base_url="https://example.test/gemini",
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.gemini_max_retries,
        request_deadline_seconds=settings.llm_request_deadline_seconds,
        client=JsonHttpClient(
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.gemini_max_retries,
            request_deadline_seconds=settings.llm_request_deadline_seconds,
            transport=httpx.MockTransport(handler),
        ),
    )
    app = create_app(
        settings,
        catalog=MatchCatalog.from_matches([match]),
        model_artifact=heuristic_artifact(),
        llm_provider=provider,
    )
    from fastapi.testclient import TestClient

    return TestClient(app), states, app.state.gemini_guard


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (429, "provider_rate_limited"),
        (503, "provider_unavailable"),
        (502, "provider_error"),
        (504, "provider_timeout"),
        (500, "provider_error"),
    ],
)
def test_http_provider_failures_return_degraded_fallback(status, reason):
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(status, json={"error": {"message": "x"}})

    client, states, manager = _gemini_client(
        handler, gemini_cache_ttl_seconds=0, match_id=f"p5-http-{status}"
    )
    response = client.post(
        f"/api/v1/matches/p5-http-{status}/explanations",
        json={
            "audience_level": "beginner",
            "sequence": states[-1].sequence,
            "question": "How is the chase going?",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["explanation_source"] == "fallback"
    assert body["degraded"] is True
    assert body["fallback_reason"] == reason
    assert "AI explanation is temporarily unavailable" in body["summary"]
    assert (
        "winner" not in body["summary"].lower()
        or "will not" in body["what_happened"].lower()
    )
    assert calls["count"] == 1
    assert manager.cache.size() == 0


def test_timeout_and_connection_failures_fallback():
    calls = {"count": 0}

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.TimeoutException("slow", request=request)

    client, states, _manager = _gemini_client(
        timeout_handler, gemini_cache_ttl_seconds=0, match_id="p5-timeout"
    )
    response = client.post(
        "/api/v1/matches/p5-timeout/explanations",
        json={"audience_level": "casual", "sequence": states[-1].sequence},
    )
    assert response.status_code == 200
    assert response.json()["fallback_reason"] == "provider_timeout"
    assert calls["count"] == 1

    calls["count"] = 0

    def connect_handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectError("down", request=request)

    client, states, _manager = _gemini_client(
        connect_handler, gemini_cache_ttl_seconds=0, match_id="p5-connect"
    )
    response = client.post(
        "/api/v1/matches/p5-connect/explanations",
        json={"audience_level": "casual", "sequence": states[-1].sequence},
    )
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "fallback"
    assert response.json()["fallback_reason"] == "provider_unavailable"
    assert calls["count"] == 1


def test_malformed_and_invalid_schema_fallback():
    def bad_json(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "not-json"}]},
                        "finishReason": "STOP",
                    }
                ]
            },
        )

    client, states, manager = _gemini_client(
        bad_json, gemini_cache_ttl_seconds=0, match_id="p5-badjson"
    )
    response = client.post(
        "/api/v1/matches/p5-badjson/explanations",
        json={"audience_level": "advanced", "sequence": states[-1].sequence},
    )
    assert response.status_code == 200
    assert response.json()["fallback_reason"] == "malformed_provider_output"
    assert manager.cache.size() == 0

    def missing_fields(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps({"summary": "only"})}]
                        },
                        "finishReason": "STOP",
                    }
                ]
            },
        )

    client, states, manager = _gemini_client(
        missing_fields, gemini_cache_ttl_seconds=0, match_id="p5-schema"
    )
    response = client.post(
        "/api/v1/matches/p5-schema/explanations",
        json={"audience_level": "beginner", "sequence": states[-1].sequence},
    )
    assert response.status_code == 200
    assert response.json()["degraded"] is True
    assert (
        is_cacheable_explanation(ExplanationResponse.model_validate(response.json()))
        is False
    )


def test_fallback_not_cached_then_successful_gemini_can_cache():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503, json={"error": "down"})
        return httpx.Response(200, json=_gemini_body())

    client, states, manager = _gemini_client(
        handler, gemini_cache_ttl_seconds=3600, match_id="p5-recover"
    )
    latest = states[-1].sequence
    first = client.post(
        "/api/v1/matches/p5-recover/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert first.status_code == 200
    assert first.json()["explanation_source"] == "fallback"
    assert manager.cache.size() == 0

    second = client.post(
        "/api/v1/matches/p5-recover/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert second.status_code == 200
    assert second.json()["explanation_source"] == "gemini"
    assert second.json()["degraded"] is False
    assert manager.cache.size() == 1

    third = client.post(
        "/api/v1/matches/p5-recover/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert third.json()["explanation_source"] == "gemini"
    assert calls["count"] == 2


def test_application_limits_degrade_without_extra_provider_calls():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_gemini_body())

    client, states, manager = _gemini_client(
        handler,
        gemini_cache_ttl_seconds=0,
        gemini_daily_request_budget=1,
        match_id="p5-budget",
    )
    latest = states[-1].sequence
    ok = client.post(
        "/api/v1/matches/p5-budget/explanations",
        json={"audience_level": "beginner", "sequence": latest},
    )
    assert ok.status_code == 200
    assert ok.json()["explanation_source"] == "gemini"
    blocked = client.post(
        "/api/v1/matches/p5-budget/explanations",
        json={"audience_level": "casual", "sequence": latest},
    )
    assert blocked.status_code == 200
    assert blocked.json()["explanation_source"] == "fallback"
    assert blocked.json()["fallback_reason"] == "daily_budget_exhausted"
    assert calls["count"] == 1
    assert manager.snapshot().daily_requests_used == 1


def test_deterministic_still_bypasses_gemini_and_quota():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("deterministic must not call Gemini")

    client, _states, manager = _gemini_client(
        handler,
        gemini_daily_request_budget=0,
        match_id="p5-det",
    )
    before = manager.snapshot().daily_requests_used
    response = client.post(
        "/api/v1/matches/p5-det/explanations",
        json={
            "audience_level": "beginner",
            "question": "What is the current score?",
        },
    )
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "deterministic"
    assert response.json()["degraded"] is False
    assert manager.snapshot().daily_requests_used == before


def test_incomplete_match_fallback_does_not_invent_winner():
    context = empty_context(match_complete=False)
    payload = build_verified_facts_fallback(
        context=context,
        audience_level=AudienceLevel.BEGINNER,
        reason="provider_error",
        question="Who will win?",
    )
    assert "will not invent a winner" in payload.what_happened.lower()
    assert "winner" not in payload.summary.lower()


def test_fallback_eligibility_and_cache_gate():
    assert is_fallback_eligible(ProviderError("x", code="timeout", status_code=504))
    assert (
        fallback_reason_for(
            ProviderError("x", code="application_rate_limited", status_code=429)
        )
        == "application_rate_limited"
    )
    degraded = ExplanationResponse.model_validate(
        {
            "summary": "s",
            "what_happened": "h",
            "why_it_matters": "w",
            "match_context": "c",
            "key_factors": ["k"],
            "audience_level": "beginner",
            "source_match_id": "m",
            "source_sequence": 1,
            "generated_at": "2026-11-15T00:00:00Z",
            "model_provider": "deterministic",
            "model_name": "pulseiq-cricket-rules-v1",
            "explanation_source": "fallback",
            "degraded": True,
            "fallback_reason": "provider_error",
        }
    )
    cache = ExplanationResponseCache(
        ttl_seconds=60, max_entries=4, monotonic=lambda: 1.0
    )
    assert is_cacheable_explanation(degraded) is False
    assert cache.put("k", degraded) is False


def test_scripted_provider_failure_degrades_for_mock_path():
    match, _ = sample_chase_match("p5-scripted")
    service = ExplanationService(
        catalog=MatchCatalog.from_matches([match]),
        provider=ScriptedProvider(
            ProviderError("down", code="provider_error", status_code=502)
        ),
        artifact=None,
        request_manager=None,
    )
    response = service.explain(
        "p5-scripted",
        AudienceLevel.CASUAL,
        question="Why does this over matter tactically?",
    )
    assert response.explanation_source == "fallback"
    assert response.degraded is True
    assert (
        "tactical" not in response.why_it_matters.lower()
        or "not" in response.why_it_matters.lower()
    )
    assert "unavailable" in response.summary.lower()
