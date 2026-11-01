"""FastAPI dependencies. Business logic stays in services."""

from __future__ import annotations

from fastapi import Request

from app.core.config import Settings
from app.services.api.catalog import MatchCatalog
from app.services.api.intelligence import IntelligenceService
from app.services.explanations.service import ExplanationService
from app.services.ml.model_registry import ModelArtifact


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_catalog(request: Request) -> MatchCatalog:
    return request.app.state.catalog


def get_model_artifact(request: Request) -> ModelArtifact | None:
    return request.app.state.model_artifact


def get_intelligence_service(request: Request) -> IntelligenceService:
    return request.app.state.intelligence


def get_explanation_service(request: Request) -> ExplanationService:
    return request.app.state.explanations
