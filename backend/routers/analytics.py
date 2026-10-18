from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from ..repositories.database import db
from ..auth import get_restaurant_id

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Impact"])

class WasteTrendPoint(BaseModel):
    day: str
    waste: float

class DashboardMetrics(BaseModel):
    inventory_risk_items: int
    pending_interventions: int
    total_waste_week_kg: float
    waste_trend_percentage: float
    financial_loss_week_inr: float
    donation_handovers: int
    waste_trend: List[WasteTrendPoint]

@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard_metrics(restaurant_id: str = Depends(get_restaurant_id)):
    now = datetime.now(timezone.utc)
    today = now.date()
    week_start = today - timedelta(days=6)
    two_week_start = today - timedelta(days=13)
    waste = db.query_collection(
        f"restaurants/{restaurant_id}/waste_records",
        [("date", ">=", two_week_start.isoformat()), ("date", "<=", today.isoformat())],
    )
    recent_waste = [record for record in waste if week_start <= date.fromisoformat(str(record["date"])[:10]) <= today]
    previous_waste = [record for record in waste if two_week_start <= date.fromisoformat(str(record["date"])[:10]) < week_start]
    recent_kg = sum(quantity_kg(record) for record in recent_waste)
    previous_kg = sum(quantity_kg(record) for record in previous_waste)
    trend = ((previous_kg - recent_kg) / previous_kg * 100) if previous_kg else 0.0
    daily_totals = {today - timedelta(days=offset): 0.0 for offset in range(6, -1, -1)}
    for record in recent_waste:
        record_day = date.fromisoformat(str(record["date"])[:10])
        daily_totals[record_day] += quantity_kg(record)
    return DashboardMetrics(
        inventory_risk_items=db.count_collection(
            f"restaurants/{restaurant_id}/inventory_items",
            [("status", "==", "reorder_recommended")],
        ),
        pending_interventions=db.count_collection(
            f"restaurants/{restaurant_id}/ai_investigations",
            [("status", "==", "PENDING_MANAGER_APPROVAL")],
        ),
        total_waste_week_kg=round(recent_kg, 2),
        waste_trend_percentage=round(trend, 1),
        financial_loss_week_inr=round(sum(float(record.get("financial_loss_inr", 0)) for record in recent_waste), 2),
        donation_handovers=db.count_collection(f"restaurants/{restaurant_id}/donation_handovers"),
        waste_trend=[
            WasteTrendPoint(day=day.strftime("%a"), waste=round(value, 3))
            for day, value in daily_totals.items()
        ],
    )

def quantity_kg(record):
    quantity = float(record.get("quantity", 0))
    unit = str(record.get("unit", "")).strip().lower()
    if unit in {"kg", "kilogram", "kilograms"}:
        return quantity
    if unit in {"g", "gm", "grm", "gram", "grams"}:
        return quantity / 1000
    return 0.0

@router.get("/waste-trend", response_model=List[WasteTrendPoint])
def get_waste_trend(restaurant_id: str = Depends(get_restaurant_id)):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=6)
    records = db.query_collection(
        f"restaurants/{restaurant_id}/waste_records",
        [("date", ">=", start.isoformat()), ("date", "<=", today.isoformat())],
    )
    totals = {}
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        totals[day] = 0.0
    for record in records:
        try:
            record_day = date.fromisoformat(str(record["date"])[:10])
        except (KeyError, TypeError, ValueError):
            continue
        if record_day in totals:
            totals[record_day] += quantity_kg(record)
    return [WasteTrendPoint(day=day.strftime("%a"), waste=round(value, 3)) for day, value in totals.items()]
