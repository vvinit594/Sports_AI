"""Shared builders for Phase 3 API and explanation tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.schemas.explanation import ExplanationContext
from app.services.api.catalog import MatchCatalog
from app.services.explanations.providers.mock import MockLLMProvider
from app.services.ml.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION
from app.services.ml.model_registry import ModelArtifact, ModelMetadata
from tests.ml_helpers import two_innings_chase


def heuristic_artifact() -> ModelArtifact:
    return ModelArtifact(
        estimator=None,
        metadata=ModelMetadata(
            model_id="test_heuristic",
            model_kind="heuristic",
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            feature_names=FEATURE_NAMES,
            trained_at="2024-01-01T00:00:00+00:00",
            target_definition="P(chasing team wins)",
            evaluation_is_meaningful=False,
            evaluation_limitation=(
                "Test heuristic only. The sample corpus is too small for a "
                "production-accurate model."
            ),
        ),
    )


def sample_chase_match(match_id: str = "api-chase-1"):
    return two_innings_chase(
        match_id=match_id,
        date="2024-01-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[1, 1, 1, 1, 1, 1, 1],
        winner="Beta",
    )


def short_chase_match(match_id: str = "api-short-1"):
    """One eligible chase state, so moment detection has nothing to pair."""

    return two_innings_chase(
        match_id=match_id,
        date="2024-02-01",
        first_innings_runs=[1, 1, 1, 1, 1, 1],
        chase_runs=[4, 4],
        winner="Beta",
        overs=1,
    )


def test_settings(**overrides: object) -> Settings:
    payload = {
        "environment": "test",
        "log_level": "WARNING",
        "cors_origins": "http://localhost:3000",
        "llm_provider": "mock",
        "llm_model": "mock-explanations-v1",
        "llm_timeout_seconds": 1.0,
        "llm_max_retries": 1,
        "max_request_bytes": 4096,
    }
    payload.update(overrides)
    return Settings.model_validate(payload)


def api_client(
    *,
    matches=None,
    artifact: ModelArtifact | None | object = "heuristic",
    provider=None,
    settings: Settings | None = None,
) -> TestClient:
    if matches is None:
        match, _ = sample_chase_match()
        catalog = MatchCatalog.from_matches([match])
    else:
        catalog = MatchCatalog.from_matches(list(matches))
    if artifact == "heuristic":
        loaded_artifact = heuristic_artifact()
    else:
        loaded_artifact = artifact  # type: ignore[assignment]
    app = create_app(
        test_settings(),
        catalog=catalog,
        model_artifact=loaded_artifact,
        llm_provider=provider or MockLLMProvider(),
    )
    if settings is not None:
        app.state.settings = settings
    return TestClient(app)


def empty_context(**overrides: object) -> ExplanationContext:
    payload = {
        "source_match_id": "ctx-1",
        "teams": ("Alpha", "Beta"),
        "batting_team": "Beta",
        "bowling_team": "Alpha",
        "innings_number": 2,
        "innings_phase": "regulation",
        "score": 10,
        "wickets": 1,
        "overs": "1.4",
        "legal_balls": 10,
        "target": 20,
        "runs_remaining": 10,
        "wickets_remaining": 9,
        "balls_remaining": 50,
        "required_run_rate": 6.0,
        "current_run_rate": 6.0,
        "sequence": 16,
        "last_delivery": None,
        "recent_deliveries": (),
        "significant_moments": (),
        "win_probability": None,
        "is_active_prediction_state": True,
        "innings_complete": False,
        "match_complete": False,
        "unknown_fields": ("last_delivery", "win_probability"),
        "notes": ("win probability unavailable: model artifact is not loaded",),
    }
    payload.update(overrides)
    return ExplanationContext.model_validate(payload)


class ScriptedProvider:
    name = "scripted"
    model_name = "scripted-test"

    def __init__(self, raw: str | Exception):
        self.raw = raw
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def generate_json(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw
