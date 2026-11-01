"""PulseIQ FastAPI application factory."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

    app.middleware("http")(_limit_request_size(resolved.max_request_bytes))
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(matches.router)
    app.include_router(intelligence.router)
    app.include_router(explanations.router)
    return app


def _limit_request_size(max_bytes: int) -> Callable:
    async def middleware(request: Request, call_next):
        length = request.headers.get("content-length")
        if length:
            try:
                size = int(length)
            except ValueError:
                size = 0
            if size > max_bytes:
                body = ErrorResponse(
                    error="Request body is too large",
                    code="request_too_large",
                )
                return JSONResponse(status_code=413, content=body.model_dump())
        return await call_next(request)

    return middleware


# Start with: python -m uvicorn app.main:create_app --factory --reload
