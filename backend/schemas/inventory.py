from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class InventoryItemBase(BaseModel):
    item_name: str
    sku: Optional[str] = None
    category: str
    brand: Optional[str] = None
    storage_location: str
    base_unit: str
    unit_cost_inr: float
    reorder_threshold: float = 0.0
    safety_stock: float = 0.0
    supplier_id: Optional[str] = None
    shelf_life_days: Optional[int] = None
    yield_factor: float = 1.0

class InventoryItemCreate(InventoryItemBase):
    current_quantity_in_store: float = 0.0
    current_quantity_in_use: float = 0.0

class InventoryItemResponse(InventoryItemBase):
    id: str
    restaurant_id: str
    current_quantity_in_store: float
    current_quantity_in_use: float
    total_current_quantity: float
    status: str
    updated_at: datetime

class StockMovementCreate(BaseModel):
    item_id: str
    movement_type: str # RECEIPT_PURCHASE, USAGE_SALES_RECIPE, USAGE_STAFF_MEAL, WASTE_RECORDED, ADJUSTMENT_AUDIT
    quantity_delta: float
    unit: str
    reference_id: Optional[str] = None
    notes: Optional[str] = None

class StockMovementResponse(StockMovementCreate):
    id: str
    restaurant_id: str
    timestamp: datetime
    balance_after: float
    created_by: str
