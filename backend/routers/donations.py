from fastapi import APIRouter, Header, Query
from typing import List
from ..schemas.donations import MatchRequest, MatchResult, HandoverRecord, HandoverResponse
from ..services import donation_service

router = APIRouter(prefix="/api/donations", tags=["Donations"])

@router.post("/match", response_model=List[MatchResult])
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
    x_restaurant_id: str = Header(default="taiken_kharadi")
):
    return donation_service.record_handover(x_restaurant_id, handover)
