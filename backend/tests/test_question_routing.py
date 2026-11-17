"""Phase 3 smarter question routing: confidence, ambiguity, Gemini guard."""

from __future__ import annotations

import json

import httpx

from app.core.config import Settings
from app.main import create_app
from app.schemas.explanation import AudienceLevel
from app.services.api.catalog import MatchCatalog
from app.services.explanations.cache import explanation_cache_key
from app.services.explanations.classifier import (
    ConfidenceLevel,
    QuestionCategory,
    classify_question,
    normalize_question,
)
from app.services.explanations.providers.gemini import GeminiProvider
from app.services.explanations.providers.http import JsonHttpClient
from tests.api_helpers import heuristic_artifact, sample_chase_match


def test_normalization_whitespace_case_punctuation_and_contractions():
    assert normalize_question("  What's   the SCORE?! ") == "what is the score"
    assert normalize_question("HOW'RE they scoring?") == "how are they scoring"
    assert normalize_question("Who's batting") == "who is batting"
    assert normalize_question("Didn't anyone get dismissed?") == (
        "did not anyone get dismissed"
    )


def test_high_confidence_natural_language_variants():
    cases = {
        "What's the score right now?": QuestionCategory.SCORE_AND_MATCH_STATE,
        "How many runs have they scored?": QuestionCategory.SCORE_AND_MATCH_STATE,
        "How many wickets are down?": QuestionCategory.SCORE_AND_MATCH_STATE,
        "Which side is batting?": QuestionCategory.SCORE_AND_MATCH_STATE,
        "What target do they need?": QuestionCategory.SCORE_AND_MATCH_STATE,
        "How far into the innings are we?": QuestionCategory.SCORE_AND_MATCH_STATE,
        "How quickly are they scoring?": QuestionCategory.RUN_RATE,
        "What's the scoring rate?": QuestionCategory.RUN_RATE,
        "How many do they need?": QuestionCategory.RUN_RATE,
        "How many runs are still required?": QuestionCategory.RUN_RATE,
        "How many deliveries are left?": QuestionCategory.RUN_RATE,
        "What's the asking rate?": QuestionCategory.RUN_RATE,
        "Tell me about the previous delivery.": QuestionCategory.DELIVERY_ANALYSIS,
        "What happened on that ball?": QuestionCategory.DELIVERY_ANALYSIS,
        "Who was on strike?": QuestionCategory.DELIVERY_ANALYSIS,
        "Who delivered the last ball?": QuestionCategory.DELIVERY_ANALYSIS,
        "Was the previous delivery a no-ball?": QuestionCategory.DELIVERY_ANALYSIS,
        "Did anyone get dismissed on that delivery?": QuestionCategory.DELIVERY_ANALYSIS,
        "How did the last over go?": QuestionCategory.RECENT_PERFORMANCE,
        "What happened in the previous six balls?": QuestionCategory.RECENT_PERFORMANCE,
        "How many runs came in the recent deliveries?": QuestionCategory.RECENT_PERFORMANCE,
        "Were there any wickets recently?": QuestionCategory.RECENT_PERFORMANCE,
        "Show me the biggest turning points.": QuestionCategory.SIGNIFICANT_MOMENTS,
        "Which deliveries had major probability swings?": QuestionCategory.SIGNIFICANT_MOMENTS,
        "When did the win probability change most?": QuestionCategory.SIGNIFICANT_MOMENTS,
        "Who won?": QuestionCategory.TERMINAL_STATE,
        "What was the final result?": QuestionCategory.TERMINAL_STATE,
        "How did the match finish?": QuestionCategory.TERMINAL_STATE,
    }
    for question, category in cases.items():
        result = classify_question(question)
        assert result.use_deterministic is True, question
        assert result.certainty is ConfidenceLevel.HIGH, question
        assert result.category is category, (question, result.category)


def test_medium_and_low_confidence_go_to_gemini_path():
    medium = {
        "How is the chase going?": "vague_question",
        "What's the match state?": "weak_category_match",
        "Tell me about the run rate": "weak_category_match",
    }
    for question, reason in medium.items():
        result = classify_question(question)
        assert result.use_deterministic is False, question
        assert result.certainty is ConfidenceLevel.MEDIUM, question
        assert result.reason == reason, (question, result.reason)

    low = {
        "What is a powerplay?": "conceptual_question",
        "Why are they under pressure?": "interpretive_question",
        "Predict who will win": "interpretive_question",
        "What is the batter economy rate?": "unsupported_statistics",
        "Give me fantasy points": "unsupported_statistics",
        "Tell me something cool": "no_explicit_category",
    }
    for question, reason in low.items():
        result = classify_question(question)
        assert result.use_deterministic is False, question
        assert result.certainty is ConfidenceLevel.LOW, question
        assert result.reason == reason, (question, result.reason)


def test_ambiguous_and_mixed_intent_questions():
    cases = [
        "What's the score and required run rate?",
        "Who is batting and who bowled the last ball?",
        "How many runs are left and why are they under pressure?",
        "What happened in the last over and was it important?",
        "Give me the score and predict who will win.",
        "What is the score and who won?",
    ]
    for question in cases:
        result = classify_question(question)
        assert result.use_deterministic is False, question
        assert result.certainty is ConfidenceLevel.LOW, question
        assert result.reason in {
            "ambiguous_question",
            "interpretive_question",
        }, (question, result.reason)


def _post(
    client, match_id: str, question: str, audience: str = "beginner", sequence=None
):
    payload = {"audience_level": audience, "question": question}
    if sequence is not None:
        payload["sequence"] = sequence
    return client.post(f"/api/v1/matches/{match_id}/explanations", json=payload)


def _gemini_body(summary: str = "Gemini summary") -> dict[str, object]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "summary": summary,
                                    "what_happened": "A ball was bowled",
                                    "why_it_matters": "It changes the chase",
                                    "match_context": "Beta are chasing",
                                    "key_factors": ["score"],
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }


def _gemini_app(handler, match, settings: Settings | None = None):
    resolved = settings or Settings.model_validate(
        {
            "environment": "test",
            "log_level": "WARNING",
            "llm_provider": "gemini",
            "llm_model": "gemini-3.8-flash",
            "gemini_api_key": "test-key",
            "gemini_max_retries": 0,
            "gemini_max_requests_per_minute": 4,
            "gemini_daily_request_budget": 12,
            "gemini_cache_ttl_seconds": 3600,
        }
    )
    provider = GeminiProvider(
        api_key="test-key",
        model_name="gemini-3.8-flash",
        base_url="https://example.test/gemini",
        timeout_seconds=1,
        max_retries=0,
        client=JsonHttpClient(
            timeout_seconds=1, max_retries=0, transport=httpx.MockTransport(handler)
        ),
    )
    app = create_app(
        resolved,
        catalog=MatchCatalog.from_matches([match]),
        model_artifact=heuristic_artifact(),
        llm_provider=provider,
    )
    from fastapi.testclient import TestClient

    return TestClient(app), app


def test_high_confidence_natural_question_bypasses_gemini_and_quota():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise AssertionError("high-confidence deterministic must not call Gemini")

    match, _ = sample_chase_match("route-high")
    client, app = _gemini_app(handler, match)
    response = _post(client, "route-high", "What's the score right now?")
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "deterministic"
    assert calls["count"] == 0
    snap = app.state.gemini_guard.snapshot()
    assert snap.requests_in_current_minute == 0
    assert snap.daily_requests_used == 0


def test_medium_confidence_uses_gemini_path():
    calls = {"count": 0}
    seen_body: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        seen_body["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_gemini_body("Medium routed"))

    match, _ = sample_chase_match("route-med")
    client, app = _gemini_app(handler, match)
    question = "How is the chase going?"
    response = _post(client, "route-med", question)
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "gemini"
    assert response.json()["summary"] == "Medium routed"
    assert calls["count"] == 1
    assert app.state.gemini_guard.snapshot().daily_requests_used == 1
    # Original phrasing is preserved for Gemini; normalization is classifier-only.
    user_text = seen_body["payload"]["contents"][0]["parts"][0]["text"]
    assert "How is the chase going?" in user_text
    assert "UNTRUSTED_USER_QUESTION" in user_text


def test_ambiguous_question_uses_gemini_not_first_regex_match():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_gemini_body("Ambiguous"))

    match, _ = sample_chase_match("route-amb")
    client, _app = _gemini_app(handler, match)
    response = _post(client, "route-amb", "What's the score and required run rate?")
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "gemini"
    assert calls["count"] == 1


def test_budget_exhausted_still_allows_high_confidence_deterministic():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("deterministic must not hit Gemini")

    match, _ = sample_chase_match("route-budget")
    settings = Settings.model_validate(
        {
            "environment": "test",
            "log_level": "WARNING",
            "llm_provider": "gemini",
            "llm_model": "gemini-3.8-flash",
            "gemini_api_key": "test-key",
            "gemini_daily_request_budget": 0,
            "gemini_max_requests_per_minute": 4,
        }
    )
    client, _app = _gemini_app(handler, match, settings=settings)
    ok = _post(client, "route-budget", "How many wickets are down?")
    assert ok.status_code == 200
    assert ok.json()["explanation_source"] == "deterministic"
    blocked = _post(client, "route-budget", "How is the chase going?")
    assert blocked.status_code == 200
    assert blocked.json()["explanation_source"] == "fallback"
    assert blocked.json()["fallback_reason"] == "daily_budget_exhausted"
    assert blocked.json()["degraded"] is True


def test_context_missing_delivery_stays_deterministic_unavailable():
    match, states = sample_chase_match("route-nodel")
    client, app = _gemini_app(
        lambda _r: (_ for _ in ()).throw(AssertionError("no gemini")), match
    )
    pre = next(state for state in states if state.last_delivery is None)
    response = _post(
        client,
        "route-nodel",
        "What happened on the last ball?",
        sequence=pre.sequence,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["explanation_source"] == "deterministic"
    assert "no last-delivery" in body["summary"].lower()
    assert app.state.gemini_guard.snapshot().daily_requests_used == 0


def test_incomplete_match_terminal_stays_deterministic_unavailable():
    match, states = sample_chase_match("route-early")
    client, _app = _gemini_app(
        lambda _r: (_ for _ in ()).throw(AssertionError("no gemini")), match
    )
    early = next(state for state in states if not state.match_complete)
    response = _post(client, "route-early", "Who won?", sequence=early.sequence)
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "deterministic"
    assert (
        "winner" in response.json()["summary"].lower()
        or "completed" in response.json()["summary"].lower()
    )


def test_moments_unavailable_without_artifact_is_deterministic():
    match, _ = sample_chase_match("route-mom")
    settings = Settings.model_validate(
        {
            "environment": "test",
            "log_level": "WARNING",
            "llm_provider": "gemini",
            "llm_model": "gemini-3.8-flash",
            "gemini_api_key": "test-key",
            "gemini_max_retries": 0,
        }
    )
    provider = GeminiProvider(
        api_key="test-key",
        model_name="gemini-3.8-flash",
        base_url="https://example.test/gemini",
        timeout_seconds=1,
        max_retries=0,
        client=JsonHttpClient(
            timeout_seconds=1,
            max_retries=0,
            transport=httpx.MockTransport(
                lambda _r: (_ for _ in ()).throw(AssertionError("no gemini"))
            ),
        ),
    )
    app = create_app(
        settings,
        catalog=MatchCatalog.from_matches([match]),
        model_artifact=None,
        llm_provider=provider,
    )
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = _post(client, "route-mom", "Show me the biggest turning points.")
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "deterministic"
    assert "unavailable" in response.json()["summary"].lower()


def test_cache_keys_differ_for_different_questions_same_match():
    key_a = explanation_cache_key(
        match_id="m1",
        sequence=10,
        audience_level=AudienceLevel.BEGINNER,
        model_id="heuristic",
        question="How is the chase going?",
    )
    key_b = explanation_cache_key(
        match_id="m1",
        sequence=10,
        audience_level=AudienceLevel.BEGINNER,
        model_id="heuristic",
        question="Why was that delivery important?",
    )
    key_c = explanation_cache_key(
        match_id="m1",
        sequence=10,
        audience_level=AudienceLevel.ADVANCED,
        model_id="heuristic",
        question="How is the chase going?",
    )
    key_d = explanation_cache_key(
        match_id="m1",
        sequence=11,
        audience_level=AudienceLevel.BEGINNER,
        model_id="heuristic",
        question="How is the chase going?",
    )
    assert key_a != key_b
    assert key_a != key_c
    assert key_a != key_d


def test_similar_normalized_questions_with_different_meaning_do_not_share_cache():
    calls = {"count": 0}
    prompts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        body = json.loads(request.content)
        prompts.append(body["contents"][0]["parts"][0]["text"])
        return httpx.Response(200, json=_gemini_body(summary=f"call-{calls['count']}"))

    match, _ = sample_chase_match("route-cache")
    client, _app = _gemini_app(handler, match)
    # Both normalize similarly around "chase"/"going" but second is interpretive.
    first = _post(client, "route-cache", "How is the chase going?")
    second = _post(client, "route-cache", "Why is the chase going under pressure?")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["summary"] != second.json()["summary"]
    assert calls["count"] == 2
    assert "How is the chase going?" in prompts[0]
    assert "Why is the chase going under pressure?" in prompts[1]


def test_omitted_question_still_uses_gemini_compat_path():
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json=_gemini_body("No question"))

    match, _ = sample_chase_match("route-omit")
    client, _app = _gemini_app(handler, match)
    response = client.post(
        "/api/v1/matches/route-omit/explanations",
        json={"audience_level": "beginner"},
    )
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "gemini"
    assert calls["count"] == 1
