from pydantic import BaseModel
from typing import List, Optional

class ReorderRecommendation(BaseModel):
    item_name: str
    current_stock: float
    expected_lead_time_demand: float
    target_stock_level: float
    recommended_purchase_quantity: float
    recommended_packs: float
    reasoning: str
    data_quality_status: str

class ReorderRequest(BaseModel):
    item_id: str
    daily_demand_forecast: float
    lead_time_days: int
    safety_stock: float
    pack_size: float = 1.0

class BuffetProductionRequest(BaseModel):
    dish_name: str
    expected_covers: int
    historical_consumption_per_cover: float
    buffer_percentage: float
    standard_batch_yield: float
    unit: str

class BuffetProductionRecommendation(BaseModel):
    dish_name: str
    expected_covers: int
    base_requirement: float
    target_production: float
    recommended_batches: int
    actual_planned_production: float
    predicted_surplus_portions: float
    unit: str
    reasoning: str
    confidence: str
