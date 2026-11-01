from tests.api_helpers import api_client, sample_chase_match


def test_match_list_returns_historical_summaries():
    match, _ = sample_chase_match("list-1")
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches")
    assert response.status_code == 200
    body = response.json()
    assert body["data_source"] == "historical_cricsheet"
    assert body["count"] == 1
    assert body["matches"][0]["source_match_id"] == "list-1"
    assert body["matches"][0]["is_historical"] is True
    assert list(body["matches"][0]["teams"]) == ["Alpha", "Beta"]


def test_match_lookup_success():
    match, states = sample_chase_match("detail-1")
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches/detail-1")
    assert response.status_code == 200
    body = response.json()
    assert body["source_match_id"] == "detail-1"
    assert body["latest_sequence"] == states[-1].sequence
    assert body["delivery_count"] == len(match.deliveries)
    assert body["is_historical"] is True


def test_unknown_match_returns_structured_404():
    match, _ = sample_chase_match()
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "match_not_found"
    assert "error" in body
    assert "Traceback" not in response.text


def test_state_retrieval_latest_and_sequence():
    match, states = sample_chase_match("state-1")
    client = api_client(matches=[match])
    latest = client.get("/api/v1/matches/state-1/state")
    assert latest.status_code == 200
    body = latest.json()
    assert body["state"]["sequence"] == states[-1].sequence
    assert body["latest_sequence"] == states[-1].sequence
    assert body["states"] is None

    mid = states[3]
    selected = client.get(f"/api/v1/matches/state-1/state?sequence={mid.sequence}")
    assert selected.status_code == 200
    selected_body = selected.json()
    assert selected_body["requested_sequence"] == mid.sequence
    assert selected_body["state"]["sequence"] == mid.sequence
    assert selected_body["state"]["innings_runs"] == mid.innings_runs
    assert selected_body["state"]["source_match_id"] == "state-1"

    full = client.get("/api/v1/matches/state-1/state?full=true")
    assert full.status_code == 200
    assert len(full.json()["states"]) == len(states)


def test_unknown_sequence_returns_404():
    match, states = sample_chase_match("seq-missing")
    client = api_client(matches=[match])
    missing = states[-1].sequence + 50
    response = client.get(f"/api/v1/matches/seq-missing/state?sequence={missing}")
    assert response.status_code == 404
    assert response.json()["code"] == "sequence_not_found"


def test_validation_failure_on_negative_sequence():
    match, _ = sample_chase_match("seq-invalid")
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches/seq-invalid/state?sequence=-1")
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["error"] == "Request validation failed"


def test_error_responses_do_not_include_stack_traces():
    match, _ = sample_chase_match()
    client = api_client(matches=[match])
    response = client.get("/api/v1/matches/missing")
    assert response.status_code == 404
    assert "traceback" not in response.text.lower()
    assert "PULSEIQ_" not in response.text
