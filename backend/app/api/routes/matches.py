"""Historical match metadata and reconstructed state."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_catalog
from app.schemas.api import (
    MatchDetail,
    MatchListResponse,
    MatchStateResponse,
)
from app.services.api.catalog import MatchCatalog, to_detail

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("", response_model=MatchListResponse)
def list_matches(catalog: MatchCatalog = Depends(get_catalog)) -> MatchListResponse:
    matches = catalog.list_summaries()
    return MatchListResponse(count=len(matches), matches=matches)


@router.get("/{match_id}", response_model=MatchDetail)
def get_match(
    match_id: str, catalog: MatchCatalog = Depends(get_catalog)
) -> MatchDetail:
    return to_detail(catalog.get(match_id))


@router.get("/{match_id}/state", response_model=MatchStateResponse)
def get_match_state(
    match_id: str,
    sequence: int | None = Query(default=None, ge=0),
    full: bool = Query(default=False),
    catalog: MatchCatalog = Depends(get_catalog),
) -> MatchStateResponse:
    loaded = catalog.get(match_id)
    state = loaded.state_at(sequence)
    return MatchStateResponse(
        source_match_id=match_id,
        requested_sequence=sequence,
        latest_sequence=loaded.latest_state.sequence,
        state=state,
        states=list(loaded.states) if full else None,
    )
