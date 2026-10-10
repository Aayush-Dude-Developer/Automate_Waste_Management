from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Impact"])

class DashboardMetrics(BaseModel):
    inventory_risk_items: int
    pending_interventions: int
    surplus_risk_portions: int
    total_waste_week_kg: float
    waste_trend_percentage: float
    financial_savings_inr: float
    meals_donated: int

@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard_metrics(x_restaurant_id: str = Header(default="taiken_kharadi")):
    # In a full production system, this aggregates data from inventory, AI investigations, and donations
    # Returning high-quality demo metrics for the final integration
    return DashboardMetrics(
        inventory_risk_items=3,
        pending_interventions=1,
        surplus_risk_portions=18,
        total_waste_week_kg=14.2,
        waste_trend_percentage=-12.5, # Reduced by 12.5% this week!
        financial_savings_inr=12500.0,
        meals_donated=145
    )
