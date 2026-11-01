"""Win-probability and significant-moment endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_intelligence_service
from app.schemas.api import MomentsResponse, WinProbabilityResponse
from app.services.api.intelligence import IntelligenceService

router = APIRouter(prefix="/api/v1/matches", tags=["intelligence"])


@router.get("/{match_id}/win-probability", response_model=WinProbabilityResponse)
def get_win_probability(
    match_id: str,
    sequence: int | None = Query(default=None, ge=0),
    service: IntelligenceService = Depends(get_intelligence_service),
) -> WinProbabilityResponse:
    return service.win_probability(match_id, sequence=sequence)


@router.get("/{match_id}/moments", response_model=MomentsResponse)
def get_moments(
    match_id: str,
    service: IntelligenceService = Depends(get_intelligence_service),
) -> MomentsResponse:
    return service.moments(match_id)
