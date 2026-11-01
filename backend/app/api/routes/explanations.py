"""Grounded GenAI explanations for a reconstructed match state."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_explanation_service
from app.schemas.explanation import ExplanationRequest, ExplanationResponse
from app.services.explanations.service import ExplanationService

router = APIRouter(prefix="/api/v1/matches", tags=["explanations"])


@router.post("/{match_id}/explanations", response_model=ExplanationResponse)
def create_explanation(
    match_id: str,
    body: ExplanationRequest,
    service: ExplanationService = Depends(get_explanation_service),
) -> ExplanationResponse:
    return service.explain(match_id, body.audience_level, body.sequence)
