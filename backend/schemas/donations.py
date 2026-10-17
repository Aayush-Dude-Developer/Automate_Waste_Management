from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DonationSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=200)


class DonationCentreSuggestion(BaseModel):
    model_config = {"str_strip_whitespace": True}

    name: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)


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
