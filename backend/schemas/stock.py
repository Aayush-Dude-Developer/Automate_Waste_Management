from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


VerificationStatus = Literal["pending", "verified", "rejected"]
PreparationStage = Literal["raw", "cleaned", "cooked", "prepared"]


class PurchaseLineCreate(BaseModel):
    ingredient_id: str
    quantity_purchased: float = Field(gt=0)
    purchase_unit: str = Field(min_length=1)
    unit_price: float = Field(ge=0)
    quantity_received: float = Field(default=0, ge=0)
    expiry_date: Optional[date] = None
    batch_number: Optional[str] = None
    usable_quantity: Optional[float] = Field(default=None, ge=0)
    usable_unit: Optional[str] = None

    @model_validator(mode="after")
    def validate_received_quantity(self):
        if self.quantity_received > self.quantity_purchased:
            raise ValueError("Quantity received cannot exceed quantity purchased.")
        if self.usable_quantity is not None and self.usable_quantity > self.quantity_received:
            raise ValueError("Usable quantity cannot exceed quantity received.")
        return self


class PurchaseInvoiceCreate(BaseModel):
    supplier_id: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    invoice_date: date
    received_date: Optional[date] = None
    total_amount: float = Field(ge=0)
    bill_document_url: Optional[str] = None
    verification_status: Literal["pending"] = "pending"
    line_items: list[PurchaseLineCreate] = Field(min_length=1)


class PurchaseLineResponse(PurchaseLineCreate):
    purchase_line_id: str
    purchase_id: str
    remaining_usable_quantity: Optional[float] = Field(default=None, ge=0)


class PurchaseInvoiceResponse(BaseModel):
    purchase_id: str
    supplier_id: str
    invoice_number: str
    invoice_date: date
    received_date: Optional[date]
    total_amount: float
    bill_document_url: Optional[str]
    verification_status: VerificationStatus
    line_items: list[PurchaseLineResponse]


class RecipeIngredientCreate(BaseModel):
    ingredient_id: str
    required_quantity: float = Field(gt=0)
    required_unit: str = Field(min_length=1)
    required_stage: str = "raw"
    yield_stage_reference: Optional[str] = None
    servings_per_batch: float = Field(default=1, gt=0)


class RecipeCreate(BaseModel):
    recipe_name: str = Field(min_length=1)
    recipe_version: str = Field(default="1", min_length=1)
    serving_size: float = Field(gt=0)
    serving_unit: str = Field(min_length=1)
    menu_category: str = Field(min_length=1)
    selling_price: float = Field(ge=0)
    is_active: bool = True
    ingredients: list[RecipeIngredientCreate] = Field(min_length=1)


class RecipeIngredientResponse(RecipeIngredientCreate):
    recipe_id: str


class RecipeResponse(BaseModel):
    recipe_id: str
    recipe_name: str
    recipe_version: str
    serving_size: float
    serving_unit: str
    menu_category: str
    selling_price: float
    is_active: bool
    ingredients: list[RecipeIngredientResponse]


class SaleCreate(BaseModel):
    sale_date: date
    recipe_id: str
    quantity_sold: float = Field(ge=0)
    quantity_cancelled: float = Field(default=0, ge=0)
    net_quantity_sold: Optional[float] = Field(default=None, ge=0)
    quantity_prepared: Optional[float] = Field(default=None, ge=0)
    net_sales_amount: float = Field(ge=0)
    sales_source: str = Field(min_length=1)
    source_reference: Optional[str] = None

    @model_validator(mode="after")
    def validate_net_quantity(self):
        calculated = max(0, self.quantity_sold - self.quantity_cancelled)
        if self.net_quantity_sold is None:
            self.net_quantity_sold = calculated
        elif self.net_quantity_sold > self.quantity_sold:
            raise ValueError("Net quantity sold cannot exceed quantity sold.")
        if self.quantity_cancelled > self.quantity_sold:
            raise ValueError("Cancelled quantity cannot exceed quantity sold.")
        return self


class SaleResponse(SaleCreate):
    sale_record_id: str
    restaurant_id: str


class StaffConsumptionCreate(BaseModel):
    consumption_date: date
    ingredient_id: Optional[str] = None
    quantity: Optional[float] = Field(default=None, gt=0)
    unit: Optional[str] = None
    recipe_id: Optional[str] = None
    portions: Optional[float] = Field(default=None, gt=0)
    staff_count: Optional[int] = Field(default=None, ge=0)
    recorded_by: str = Field(min_length=1)
    source_reference: Optional[str] = None

    @model_validator(mode="after")
    def require_ingredient_or_recipe(self):
        if self.recipe_id:
            if self.portions is None:
                raise ValueError("Portions are required when recording staff consumption by recipe.")
        elif not (self.ingredient_id and self.quantity and self.unit):
            raise ValueError("Provide an ingredient, quantity, and unit, or a recipe and portions.")
        return self


class StaffConsumptionResponse(StaffConsumptionCreate):
    consumption_id: str
    restaurant_id: str


class WasteRecordCreateV2(BaseModel):
    waste_date: date
    ingredient_id: str
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1)
    waste_reason: str = Field(min_length=1)
    stage: str = "raw"
    estimated_cost: Optional[float] = Field(default=None, ge=0)
    recorded_by: str = Field(min_length=1)
    recipe_id: Optional[str] = None
    waste_type: Literal["raw_ingredient", "prepared_food"] = "raw_ingredient"


class WasteRecordResponseV2(WasteRecordCreateV2):
    waste_record_id: str
    restaurant_id: str


class PhysicalStocktake(BaseModel):
    actual_closing_stock: float = Field(ge=0)
    verified_by: str = Field(min_length=1)


class MonthlyStockBalance(BaseModel):
    ingredient_id: str
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    opening_stock: float = Field(ge=0)
    total_purchased_stock: float = Field(ge=0)
    total_recipe_consumption: float = Field(ge=0)
    total_staff_consumption: float = Field(ge=0)
    total_wasted_stock: float = Field(ge=0)
    other_stock_inflows: float = Field(ge=0)
    other_stock_outflows: float = Field(ge=0)
    calculated_closing_stock: float
    actual_closing_stock: Optional[float] = Field(default=None, ge=0)
    stock_variance: Optional[float] = None
    physical_count_verified: bool = False
    provisional: bool = True


class TheoreticalConsumption(BaseModel):
    ingredient_id: str
    item_name: str
    month: str
    unit: str
    theoretical_raw_consumption: float
