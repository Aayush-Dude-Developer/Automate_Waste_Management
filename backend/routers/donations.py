from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from ..auth import get_restaurant_id, get_current_user
from ..schemas.donations import (
    DonationCentreSuggestion,
    DonationSearchRequest,
    HandoverRecord,
    HandoverResponse,
)
from ..services import donation_service

router = APIRouter(prefix="/api/donations", tags=["Donations"])

@router.post("/search", response_model=List[DonationCentreSuggestion], dependencies=[Depends(get_current_user)])
def search_donation_centres(request: DonationSearchRequest):
    try:
        return donation_service.search_donation_centres(request.query)
    except donation_service.DonationSearchError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error

@router.post("/handover", response_model=HandoverResponse)
def log_donation_handover(
    handover: HandoverRecord,
    restaurant_id: str = Depends(get_restaurant_id)
):
    return donation_service.record_handover(restaurant_id, handover)

@router.get("/handovers", response_model=List[HandoverResponse])
def get_donation_handovers(
    limit: int | None = Query(default=None, ge=1, le=500),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return donation_service.get_handovers(restaurant_id, limit)
