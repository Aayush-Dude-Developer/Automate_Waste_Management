from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ExtractionPreviewResponse(BaseModel):
    document_id: str
    document_type_hint: Optional[str]
    extracted_records: List[Dict[str, Any]]
    confidence_score: float
    ambiguous_fields: List[str]
    duplicate_warning: bool

class ConfirmImportRequest(BaseModel):
    document_id: str
    confirmed_records: List[Dict[str, Any]]
    target_entity: str # 'waste_records', 'staff_meal_records', 'inventory_items'
