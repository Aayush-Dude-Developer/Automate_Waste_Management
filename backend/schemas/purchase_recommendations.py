from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


RecommendationStatus = Literal["needs_review", "approved", "ordered", "received"]


class RecommendationStatusUpdate(BaseModel):
    status: Literal["approved", "ordered", "received"]
    ingredient_id: str = Field(min_length=1)
    forecast_start_date: date
    forecast_period_days: int = Field(ge=1, le=28)
    order_reference: str | None = Field(default=None, max_length=120)
    expected_delivery_date: date | None = None
    purchase_line_id: str | None = None


class RecommendationDemandBasis(BaseModel):
    recipe_id: str
    recipe_name: str
    forecast_portions: float
    raw_quantity_per_portion: float
    trend_factor: float = 1.0
    unit: str
    yield_stages_applied: list[str] = Field(default_factory=list)


class RecommendationIncomingOrder(BaseModel):
    recommendation_id: str
    quantity: float
    expected_delivery_date: date
    expiry_date: date | None = None
    order_reference: str


class RecommendationExpiryBatch(BaseModel):
    purchase_id: str
    batch_number: str | None
    expiry_date: date
    quantity_received: float
    remaining_usable_quantity: float = 0
    expired: bool = False
    unit: str


class PurchaseRecommendation(BaseModel):
    recommendation_id: str
    ingredient_id: str
    ingredient_name: str
    forecast_start_date: date
    forecast_period_days: int
    current_usable_stock: float
    forecast_start_usable_stock: float
    stock_unit: str
    stock_source: str
    forecast_daily_consumption: float
    reorder_threshold: float
    safety_stock: float
    supplier_id: str | None
    supplier_lead_time_days: int | None
    projected_stockout_date: date | None
    recommended_order_date: date | None
    recommended_delivery_date: date | None = None
    recommended_expiry_date: date | None = None
    recommended_purchase_quantity: float
    estimated_purchase_cost: float | None
    priority: Literal["critical", "high", "medium", "low"]
    status: RecommendationStatus | Literal["no_action"]
    explanation: str
    explanation_points: list[str] = Field(default_factory=list)
    reliability_warnings: list[str] = Field(default_factory=list)
    demand_forecast: dict[str, float] = Field(default_factory=dict)
    expiry_losses_by_day: dict[str, float] = Field(default_factory=dict)
    sales_basis: list[RecommendationDemandBasis] = Field(default_factory=list)
    incoming_orders: list[RecommendationIncomingOrder] = Field(default_factory=list)
    expiry_batches: list[RecommendationExpiryBatch] = Field(default_factory=list)
    expected_delivery_date: date | None = None
    order_reference: str | None = None
    purchase_line_id: str | None = None


class PurchaseRecommendationDashboard(BaseModel):
    forecast_period_days: int
    forecast_start_date: date
    generated_at: str
    ingredients_requiring_replenishment: int
    upcoming_stockout_risks: int
    recommendations_awaiting_approval: int
    data_warnings: list[str] = Field(default_factory=list)
    recommendations: list[PurchaseRecommendation]
