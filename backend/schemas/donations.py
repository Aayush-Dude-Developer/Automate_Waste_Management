from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DonationCentreBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accepts_cooked_food: Optional[bool] = None
    accepts_raw_produce: Optional[bool] = None
    requires_cold_chain: Optional[bool] = None
    minimum_quantity_kg: Optional[float] = None
    pickup_service_available: Optional[bool] = None
    google_maps_link: Optional[str] = None
    opening_hours: Optional[str] = None
    accepts_vegetarian: Optional[bool] = None
    accepts_non_vegetarian: Optional[bool] = None
    website_url: Optional[str] = None
    source_urls: List[str] = Field(default_factory=list)

class DonationCentre(DonationCentreBase):
    id: str
    verified: bool

class MatchRequest(BaseModel):
    item_name: str
    quantity_kg: float = Field(gt=0)
    is_cooked: bool
    requires_cold_chain: bool
    is_vegetarian: Optional[bool] = None
    location_area: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)
    state: Optional[str] = Field(default=None, max_length=120)
    country: Optional[str] = Field(default=None, max_length=120)
    pincode: Optional[str] = Field(default=None, max_length=20)

class MatchResult(BaseModel):
    centre: DonationCentre
    match_score: int
    distance_km: Optional[float] = None
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
