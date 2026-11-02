"""Request-body size limit uses actual bytes, not only Content-Length."""

from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.api.catalog import MatchCatalog
from tests.api_helpers import (
    MockLLMProvider,
    heuristic_artifact,
    sample_chase_match,
)
from tests.api_helpers import test_settings as settings_for_tests

MAX_BYTES = 64
PATH = "/api/v1/matches/size-1/explanations"
SMALL_JSON = b'{"audience_level":"beginner"}'


def _app():
    match, _ = sample_chase_match("size-1")
    return create_app(
        settings_for_tests(max_request_bytes=MAX_BYTES),
        catalog=MatchCatalog.from_matches([match]),
        model_artifact=heuristic_artifact(),
        llm_provider=MockLLMProvider(),
    )


def _asgi_post(
    app,
    *,
    chunks: list[bytes],
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict]:
    headers = [
        (b"host", b"testserver"),
        (b"content-type", b"application/json"),
    ]
    if extra_headers:
        headers.extend(extra_headers)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": PATH,
        "raw_path": PATH.encode(),
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    pending = list(chunks)
    sent: list[dict] = []

    async def receive() -> dict:
        if pending:
            body = pending.pop(0)
            return {
                "type": "http.request",
                "body": body,
                "more_body": bool(pending),
            }
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    start = next(item for item in sent if item["type"] == "http.response.start")
    payload = b"".join(
        item.get("body", b"") for item in sent if item["type"] == "http.response.body"
    )
    return start["status"], json.loads(payload.decode())


def test_payload_exceeding_limit_with_content_length():
    client = TestClient(_app())
    oversized = {"audience_level": "beginner", "padding": "x" * MAX_BYTES}
    response = client.post(PATH, json=oversized)
    assert response.status_code == 413
    body = response.json()
    assert body["code"] == "request_too_large"
    assert body["error"] == "Request body is too large"


def test_payload_exceeding_limit_without_content_length():
    chunk = b"x" * (MAX_BYTES // 2)
    status, body = _asgi_post(_app(), chunks=[chunk, chunk, chunk])
    assert status == 413
    assert body["code"] == "request_too_large"
    assert body["error"] == "Request body is too large"


def test_payload_within_the_limit():
    client = TestClient(_app())
    response = client.post(PATH, json={"audience_level": "beginner"})
    assert response.status_code == 200
    body = response.json()
    assert body["audience_level"] == "beginner"
    assert body["source_match_id"] == "size-1"
    health = client.get("/health")
    assert health.status_code == 200


def test_malformed_content_length_is_rejected_safely():
    status, body = _asgi_post(
        _app(),
        chunks=[SMALL_JSON],
        extra_headers=[(b"content-length", b"not-a-number")],
    )
    assert status == 400
    assert body["code"] == "invalid_content_length"
    assert "error" in body
    assert "Traceback" not in body["error"]

    negative, negative_body = _asgi_post(
        _app(),
        chunks=[SMALL_JSON],
        extra_headers=[(b"content-length", b"-10")],
    )
    assert negative == 400
    assert negative_body["code"] == "invalid_content_length"
