from fastapi import APIRouter, Header, HTTPException
from typing import List
from ..schemas.planning import ReorderRecommendation, ReorderRequest, BuffetProductionRequest, BuffetProductionRecommendation
from ..engines.forecasting_engine import calculate_reorder_quantity
from ..engines.buffet_engine import calculate_buffet_production
from ..services.inventory_service import get_inventory_item

router = APIRouter(prefix="/api/planning", tags=["Planning & Forecasting"])

@router.post("/replenishment", response_model=ReorderRecommendation)
def get_replenishment_recommendation(
    request: ReorderRequest,
    x_restaurant_id: str = Header(default="taiken_kharadi")
):
    item = get_inventory_item(x_restaurant_id, request.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Call the deterministic engine
    result = calculate_reorder_quantity(
        item_name=item.item_name,
        current_stock=item.total_current_quantity,
        incoming_stock=0.0, # Could be fetched from a purchase_orders collection
        daily_demand_forecast=request.daily_demand_forecast,
        lead_time_days=request.lead_time_days,
        safety_stock=request.safety_stock,
        pack_size=request.pack_size
    )
    return result

@router.post("/buffet", response_model=BuffetProductionRecommendation)
def get_buffet_production_plan(
    request: BuffetProductionRequest,
    x_restaurant_id: str = Header(default="taiken_kharadi")
):
    result = calculate_buffet_production(
        dish_name=request.dish_name,
        expected_covers=request.expected_covers,
        historical_consumption_per_cover=request.historical_consumption_per_cover,
        buffer_percentage=request.buffer_percentage,
        standard_batch_yield=request.standard_batch_yield,
        unit=request.unit
    )
    return result
