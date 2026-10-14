from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from ..auth import get_restaurant_id, get_current_user
from ..schemas.donations import MatchRequest, MatchResult, HandoverRecord, HandoverResponse
from ..services import donation_service

router = APIRouter(prefix="/api/donations", tags=["Donations"])

@router.post("/match", response_model=List[MatchResult], dependencies=[Depends(get_current_user)])
def get_donation_matches(
    request: MatchRequest,
    lat: float | None = Query(None),
    lon: float | None = Query(None),
    use_ai: bool = Query(False),
    location_name: str | None = Query(None),
):
    try:
        return donation_service.find_matches(
            request,
            lat,
            lon,
            use_ai_discovery=use_ai,
            location_name=location_name,
        )
    except donation_service.DonationDiscoveryRateLimited as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except donation_service.DonationDiscoveryUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except donation_service.DonationDiscoveryError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

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
