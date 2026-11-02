"""PulseIQ FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.errors import register_exception_handlers
from app.api.routes import explanations, health, intelligence, matches
from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderError
from app.core.logging import setup_logging
from app.schemas.api import ErrorResponse
from app.services.api.catalog import MatchCatalog
from app.services.api.intelligence import IntelligenceService, load_optional_model
from app.services.explanations.providers.factory import build_provider
from app.services.explanations.service import ExplanationService, UnavailableProvider
from app.services.ml.model_registry import ModelArtifact

_UNSET = object()


def create_app(
    settings: Settings | None = None,
    *,
    catalog: MatchCatalog | None = None,
    model_artifact: ModelArtifact | None | object = _UNSET,
    llm_provider: object | None = None,
) -> FastAPI:
    resolved = settings or get_settings()
    setup_logging(resolved.log_level)

    app = FastAPI(
        title=resolved.api_title,
        version=resolved.api_version,
        summary="Historical cricket intelligence API for PulseIQ Phase 3.",
        description=(
            "Exposes reconstructed Cricsheet match state, chase win-probability, "
            "significant moments, and grounded explanations. Sample files are "
            "historical, not live matches. The current model corpus is too small "
            "for production-accurate probabilities."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )

    loaded_catalog = catalog or MatchCatalog.from_directory(
        resolved.resolved_cricsheet_dir()
    )
    if model_artifact is _UNSET:
        artifact = load_optional_model(resolved)
    else:
        artifact = model_artifact  # type: ignore[assignment]

    if llm_provider is not None:
        provider = llm_provider
    else:
        try:
            provider = build_provider(resolved)
        except ProviderError as exc:
            provider = UnavailableProvider(exc)

    app.state.settings = resolved
    app.state.catalog = loaded_catalog
    app.state.model_artifact = artifact
    app.state.intelligence = IntelligenceService(loaded_catalog, artifact)
    app.state.explanations = ExplanationService(loaded_catalog, provider, artifact)

    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=resolved.max_request_bytes)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(matches.router)
    app.include_router(intelligence.router)
    app.include_router(explanations.router)
    return app


class RequestSizeLimitMiddleware:
    """Reject request bodies larger than ``max_bytes``.

    ``Content-Length`` is an early hint only. The actual ASGI body is counted
    in chunks so missing, chunked, or lying length headers cannot bypass the
    limit. At most ``max_bytes`` body bytes are buffered, then replayed so
    FastAPI can still parse a valid payload.
    """

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _declared_content_length(scope)
        if declared is _MALFORMED:
            await _send_error(
                send,
                status_code=400,
                error="Invalid Content-Length header",
                code="invalid_content_length",
            )
            return
        if declared is not None and declared > self.max_bytes:
            await _send_error(
                send,
                status_code=413,
                error="Request body is too large",
                code="request_too_large",
            )
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                await self.app(
                    scope, _replay_body(bytes(body), disconnected=True), send
                )
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            if chunk:
                if len(body) + len(chunk) > self.max_bytes:
                    await _send_error(
                        send,
                        status_code=413,
                        error="Request body is too large",
                        code="request_too_large",
                    )
                    return
                body.extend(chunk)
            if not message.get("more_body", False):
                break

        await self.app(scope, _replay_body(bytes(body)), send)


_MALFORMED = object()


def _declared_content_length(scope: Scope) -> int | object | None:
    raw = None
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            raw = value.decode("latin-1")
            break
    if raw is None:
        return None
    stripped = raw.strip()
    if stripped == "" or not stripped.isdigit():
        return _MALFORMED
    return int(stripped)


def _replay_body(body: bytes, *, disconnected: bool = False) -> Receive:
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if disconnected and not sent:
            sent = True
            return {"type": "http.disconnect"}
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


async def _send_error(send: Send, *, status_code: int, error: str, code: str) -> None:
    payload = ErrorResponse(error=error, code=code).model_dump_json().encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


# Start with: python -m uvicorn app.main:create_app --factory --reload
