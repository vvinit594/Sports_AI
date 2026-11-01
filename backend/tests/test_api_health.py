from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.api.catalog import MatchCatalog
from tests.api_helpers import MockLLMProvider, heuristic_artifact, sample_chase_match


def test_health_endpoint_ok():
    match, _ = sample_chase_match()
    client = TestClient(
        create_app(
            Settings.model_validate({"llm_provider": "mock", "log_level": "WARNING"}),
            catalog=MatchCatalog.from_matches([match]),
            model_artifact=heuristic_artifact(),
            llm_provider=MockLLMProvider(),
        )
    )
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "pulseiq"
    assert body["phase"] == 3


def test_readiness_endpoint_ready():
    match, _ = sample_chase_match()
    client = TestClient(
        create_app(
            Settings.model_validate(
                {
                    "llm_provider": "mock",
                    "log_level": "WARNING",
                    "cors_origins": "http://localhost:3000",
                }
            ),
            catalog=MatchCatalog.from_matches([match]),
            model_artifact=heuristic_artifact(),
            llm_provider=MockLLMProvider(),
        )
    )
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["catalog_loaded"] is True
    assert body["match_count"] == 1
    assert body["data_source"] == "historical_cricsheet"
    assert body["model_loaded"] is True
    assert body["llm_provider"] == "mock"
    assert "GEMINI_API_KEY" not in response.text
    assert "OPENAI_API_KEY" not in response.text


def test_readiness_not_ready_when_catalog_directory_missing(tmp_path):
    missing = tmp_path / "no-such-cricsheet"
    client = TestClient(
        create_app(
            Settings.model_validate(
                {
                    "llm_provider": "mock",
                    "log_level": "WARNING",
                    "cricsheet_dir": str(missing),
                }
            ),
            model_artifact=None,
            llm_provider=MockLLMProvider(),
        )
    )
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["catalog_loaded"] is False
    assert body["model_loaded"] is False
