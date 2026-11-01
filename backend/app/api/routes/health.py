"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.api import HealthResponse, ReadinessResponse
from app.services.explanations.providers.factory import provider_is_configured

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/api/v1/health/ready", response_model=ReadinessResponse)
def ready(request: Request) -> ReadinessResponse | JSONResponse:
    catalog = request.app.state.catalog
    settings = request.app.state.settings
    catalog_loaded = catalog.ready()
    model_loaded = request.app.state.model_artifact is not None
    llm_configured = provider_is_configured(settings)
    is_ready = catalog_loaded
    body = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        catalog_loaded=catalog_loaded,
        match_count=catalog.count(),
        model_loaded=model_loaded,
        llm_provider=settings.normalized_llm_provider(),
        llm_configured=llm_configured,
    )
    if not is_ready:
        return JSONResponse(status_code=503, content=body.model_dump())
    return body
