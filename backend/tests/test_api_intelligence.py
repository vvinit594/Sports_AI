from app.services.ml.features import is_chase_training_state
from tests.api_helpers import (
    api_client,
    sample_chase_match,
    short_chase_match,
)


def test_win_probability_integration_for_eligible_chase():
    match, states = sample_chase_match("wp-1")
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches/wp-1/win-probability")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["unavailable_reason"] is None
    assert body["data_source"] == "historical_cricsheet"
    assert body["predictions"]
    assert body["model"]["model_id"] == "test_heuristic"
    assert body["model"]["evaluation_is_meaningful"] is False
    assert body["model"]["evaluation_limitation"]
    eligible = [state.sequence for state in states if is_chase_training_state(state)]
    returned = [item["sequence"] for item in body["predictions"]]
    assert returned == eligible
    for item in body["predictions"]:
        assert 0.0 <= item["probability"] <= 1.0
        assert item["source_match_id"] == "wp-1"


def test_win_probability_missing_model_artifact():
    match, _ = sample_chase_match("wp-missing")
    client = api_client(matches=[match], artifact=None)
    response = client.get("/api/v1/matches/wp-missing/win-probability")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["unavailable_reason"] == "model_artifact_missing"
    assert body["predictions"] == []
    assert body["model"] is None


def test_win_probability_unsupported_state():
    match, states = sample_chase_match("wp-unsupported")
    client = api_client(matches=[match])
    first_innings = next(
        state.sequence
        for state in states
        if state.sequence > 0 and not is_chase_training_state(state)
    )
    response = client.get(
        f"/api/v1/matches/wp-unsupported/win-probability?sequence={first_innings}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["unavailable_reason"] == "unsupported_state"
    assert body["predictions"] == []
    assert body["model"] is not None


def test_win_probability_single_eligible_sequence():
    match, states = sample_chase_match("wp-seq")
    client = api_client(matches=[match])
    chase_seq = next(
        state.sequence for state in states if is_chase_training_state(state)
    )
    response = client.get(
        f"/api/v1/matches/wp-seq/win-probability?sequence={chase_seq}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert len(body["predictions"]) == 1
    assert body["predictions"][0]["sequence"] == chase_seq
    assert 0.0 <= body["predictions"][0]["probability"] <= 1.0


def test_moments_endpoint_with_predictions():
    match, _ = sample_chase_match("mom-1")
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches/mom-1/moments")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["count"] == len(body["moments"])
    assert body["source_match_id"] == "mom-1"
    for moment in body["moments"]:
        assert moment["source_match_id"] == "mom-1"
        assert moment["sequence"] >= 0
        assert moment["moment_type"]


def test_moments_empty_when_nothing_to_pair():
    match, _ = short_chase_match("mom-empty")
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches/mom-empty/moments")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["count"] == 0
    assert body["moments"] == []


def test_moments_missing_model_does_not_fabricate_events():
    match, _ = sample_chase_match("mom-missing")
    client = api_client(matches=[match], artifact=None)
    response = client.get("/api/v1/matches/mom-missing/moments")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["unavailable_reason"] == "model_artifact_missing"
    assert body["moments"] == []
