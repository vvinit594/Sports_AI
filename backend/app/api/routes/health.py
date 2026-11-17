"""Liveness and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.api import HealthResponse, LlmUsageView, ReadinessResponse
from app.services.explanations.providers.factory import (
    provider_is_configured,
    resolved_llm_model,
)

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
    usage = None
    manager = getattr(request.app.state, "gemini_guard", None)
    if manager is not None:
        snap = manager.snapshot()
        usage = LlmUsageView(
            storage="process_local",
            max_requests_per_minute=snap.max_requests_per_minute,
            requests_in_current_minute=snap.requests_in_current_minute,
            daily_request_budget=snap.daily_request_budget,
            daily_requests_used=snap.daily_requests_used,
            daily_resets_at_utc=snap.daily_resets_at_utc,
            max_concurrent_requests=snap.max_concurrent_requests,
            cache_entries=snap.cache_entries,
            cache_ttl_seconds=snap.cache_ttl_seconds,
            resets_on_process_restart=snap.resets_on_process_restart,
            cache_hits=snap.cache_hits,
            cache_misses=snap.cache_misses,
            cache_coalesce_hits=snap.cache_coalesce_hits,
            cache_expirations=snap.cache_expirations,
            cache_lru_evictions=snap.cache_lru_evictions,
        )
    body = ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        catalog_loaded=catalog_loaded,
        match_count=catalog.count(),
        model_loaded=model_loaded,
        llm_provider=settings.normalized_llm_provider(),
        llm_configured=llm_configured,
        llm_model=resolved_llm_model(settings),
        llm_usage=usage,
    )
    if not is_ready:
        return JSONResponse(status_code=503, content=body.model_dump())
    return body
