from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DonationCentreBase(BaseModel):
    name: str
    contact_person: str
    phone: str
    address: str
    latitude: float
    longitude: float
    accepts_cooked_food: bool
    accepts_raw_produce: bool
    requires_cold_chain: bool
    minimum_quantity_kg: float
    pickup_service_available: bool

class DonationCentre(DonationCentreBase):
    id: str
    verified: bool

class MatchRequest(BaseModel):
    item_name: str
    quantity_kg: float
    is_cooked: bool
    requires_cold_chain: bool

class MatchResult(BaseModel):
    centre: DonationCentre
    match_score: int
    distance_km: float
    eligibility_notes: List[str]
    is_eligible: bool

class HandoverRecord(BaseModel):
    item_name: str
    quantity_kg: float
    centre_id: str
    driver_name: Optional[str]
    temperature_at_handover: Optional[float]
    notes: Optional[str]

class HandoverResponse(HandoverRecord):
    id: str
    restaurant_id: str
    status: str
    timestamp: datetime
