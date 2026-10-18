from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional, List
from datetime import datetime

class YieldStage(BaseModel):
    stage_name: str
    input_stage: str
    output_stage: str
    input_unit: str
    output_unit: str
    yield_percentage: float

    @model_validator(mode="after")
    def validate_yield(self):
        if self.yield_percentage <= -100:
            raise ValueError("Yield percentage must be greater than -100.")
        return self

class InventoryItemBase(BaseModel):
    item_name: str
    sku: Optional[str] = None
    category: str = "Uncategorized"
    brand: Optional[str] = None
    storage_location: str = "Unspecified"
    base_unit: str = "kg"
    unit_cost_inr: Optional[float] = Field(default=None, ge=0)
    ingredient_id: Optional[str] = None
    unit_cost: Optional[float] = Field(default=None, ge=0)
    input_unit: Optional[str] = None
    output_unit: Optional[str] = None
    yield_percentage: float = 0.0
    yield_type: Literal["negative", "positive", "no change"] = "no change"
    yield_stage: Optional[str] = None
    yield_stages: List[YieldStage] = Field(default_factory=list)
    reorder_threshold: float = Field(default=0.0, ge=0)
    safety_stock: float = Field(default=0.0, ge=0)
    supplier_id: Optional[str] = None
    minimum_order_quantity: Optional[float] = Field(default=None, gt=0)
    pack_size: Optional[float] = Field(default=None, gt=0)
    lot_tracking_enabled: bool = False
    untracked_stock_quantity: Optional[float] = Field(default=0.0, ge=0)
    shelf_life_days: Optional[int] = None
    yield_factor: float = 1.0
    lead_time_days: int = Field(default=0, ge=0)

    @model_validator(mode="before")
    @classmethod
    def accept_current_and_new_field_names(cls, values):
        if not isinstance(values, dict):
            return values
        values = values.copy()
        aliases = {
            "unit_cost": "unit_cost_inr",
            "input_unit": "base_unit",
            "stock_in_store": "current_quantity_in_store",
            "stock_in_use": "current_quantity_in_use",
        }
        for new_name, old_name in aliases.items():
            if new_name in values and old_name not in values:
                values[old_name] = values[new_name]
            elif old_name in values and new_name not in values:
                values[new_name] = values[old_name]
        return values

    @model_validator(mode="after")
    def validate_yield_and_cost(self):
        if self.yield_percentage <= -100:
            raise ValueError("Yield percentage must be greater than -100.")
        if self.unit_cost is None and self.unit_cost_inr is None:
            raise ValueError("Provide unit_cost or unit_cost_inr.")
        if self.unit_cost is None:
            self.unit_cost = self.unit_cost_inr
        if self.unit_cost_inr is None:
            self.unit_cost_inr = self.unit_cost
        self.yield_type = (
            "negative" if self.yield_percentage < 0 else
            "positive" if self.yield_percentage > 0 else
            "no change"
        )
        self.input_unit = self.input_unit or self.base_unit
        self.base_unit = self.base_unit or self.input_unit
        self.output_unit = self.output_unit or self.input_unit
        return self

class InventoryItemCreate(InventoryItemBase):
    current_quantity_in_store: float = Field(default=0.0, ge=0)
    current_quantity_in_use: float = Field(default=0.0, ge=0)
    stock_in_store: Optional[float] = Field(default=None, ge=0)
    stock_in_use: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="after")
    def synchronize_stock_fields(self):
        if self.stock_in_store is None:
            self.stock_in_store = self.current_quantity_in_store
        if self.stock_in_use is None:
            self.stock_in_use = self.current_quantity_in_use
        return self

class InventoryItemResponse(InventoryItemBase):
    id: str
    restaurant_id: str
    ingredient_id: Optional[str] = None
    current_quantity_in_store: float
    current_quantity_in_use: float
    stock_in_store: Optional[float] = None
    stock_in_use: Optional[float] = None
    total_current_quantity: float
    status: str
    updated_at: datetime

    @model_validator(mode="after")
    def synchronize_response_fields(self):
        self.ingredient_id = self.ingredient_id or self.id
        self.stock_in_store = self.current_quantity_in_store
        self.stock_in_use = self.current_quantity_in_use
        return self

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
