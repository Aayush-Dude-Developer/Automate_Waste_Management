from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class WasteRecordCreate(BaseModel):
    date: str
    item_name: str
    inventory_item_id: Optional[str] = None
    quantity: float
    unit: str
    reason: str
    checked_by: str
    source_document_id: Optional[str] = None

class WasteRecordResponse(WasteRecordCreate):
    id: str
    restaurant_id: str
    financial_loss_inr: float
    status: str
    created_at: datetime

class StaffMealItem(BaseModel):
    ingredient_name: str
    inventory_item_id: Optional[str] = None
    quantity: float
    unit: str
    remarks: Optional[str] = None

class StaffMealRecordCreate(BaseModel):
    date: str
    shift: str
    staff_on_shift_count: int
    prepared_by: str
    verified_by_duty_manager: str
    items: List[StaffMealItem]
    source_document_id: Optional[str] = None

class StaffMealRecordResponse(StaffMealRecordCreate):
    id: str
    restaurant_id: str
    total_cost_inr: float
    deducted_from_inventory: bool
    created_at: datetime
