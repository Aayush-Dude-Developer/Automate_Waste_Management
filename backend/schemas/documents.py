from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ExtractionPreviewResponse(BaseModel):
    document_id: str
    document_type_hint: Optional[str]
    available_fields: List[str]
    extracted_records: List[Dict[str, Any]]
    confidence_score: float
    ambiguous_fields: List[str]
    duplicate_warning: bool
    message: str = ""

class ConfirmImportRequest(BaseModel):
    document_id: str
    confirmed_records: List[Dict[str, Any]]
    target_entity: str # 'waste_records', 'staff_meal_records', 'inventory_items'


class AmendRecordsRequest(BaseModel):
    target_entity: str
    current_records: List[Dict[str, Any]] = Field(max_length=100)
    amendment: str = Field(min_length=1, max_length=2000)


class AmendRecordsResponse(BaseModel):
    updated_records: List[Dict[str, Any]]
    message: str
