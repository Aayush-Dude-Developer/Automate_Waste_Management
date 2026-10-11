from fastapi import APIRouter, Depends, Query
from typing import List
from ..auth import get_restaurant_id, get_current_user
from ..schemas.donations import MatchRequest, MatchResult, HandoverRecord, HandoverResponse
from ..services import donation_service

router = APIRouter(prefix="/api/donations", tags=["Donations"])

@router.post("/match", response_model=List[MatchResult], dependencies=[Depends(get_current_user)])
def get_donation_matches(
    request: MatchRequest,
    lat: float = Query(18.5515), # Default to Taiken Kharadi lat
    lon: float = Query(73.9348),  # Default to Taiken Kharadi lon
    use_ai: bool = Query(False),
    location_name: str = Query("Pune")
):
    return donation_service.find_matches(request, lat, lon, use_ai_discovery=use_ai, location_name=location_name)

@router.post("/handover", response_model=HandoverResponse)
def log_donation_handover(
    handover: HandoverRecord,
    restaurant_id: str = Depends(get_restaurant_id)
):
    return donation_service.record_handover(restaurant_id, handover)

@router.get("/handovers", response_model=List[HandoverResponse])
def get_donation_handovers(restaurant_id: str = Depends(get_restaurant_id)):
    return donation_service.get_handovers(restaurant_id)
