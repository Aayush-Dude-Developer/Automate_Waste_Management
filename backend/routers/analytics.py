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

@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard_metrics(restaurant_id: str = Depends(get_restaurant_id)):
    waste = db.get_collection(f"restaurants/{restaurant_id}/waste_records")
    inventory = db.get_collection(f"restaurants/{restaurant_id}/inventory_items")
    investigations = db.get_collection(f"restaurants/{restaurant_id}/ai_investigations")
    handovers = db.get_collection(f"restaurants/{restaurant_id}/donation_handovers")
    now = datetime.now(timezone.utc)
    start = now.date() - timedelta(days=6)

    def record_date(record):
        raw_date = record.get("date") or record.get("created_at")
        if not raw_date:
            return None
        try:
            return datetime.fromisoformat(str(raw_date).replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                return None

    def quantity_kg(record):
        quantity = float(record.get("quantity", 0))
        unit = str(record.get("unit", "")).strip().lower()
        if unit in {"kg", "kilogram", "kilograms"}:
            return quantity
        if unit in {"g", "gm", "grm", "gram", "grams"}:
            return quantity / 1000
        return 0.0

    recent_waste = [record for record in waste if start <= (record_date(record) or date.min) <= now.date()]
    previous_start = start - timedelta(days=7)
    previous_waste = [record for record in waste if previous_start <= (record_date(record) or date.min) < start]
    recent_kg = sum(quantity_kg(record) for record in recent_waste)
    previous_kg = sum(quantity_kg(record) for record in previous_waste)
    trend = ((previous_kg - recent_kg) / previous_kg * 100) if previous_kg else 0.0
    pending = sum(1 for record in investigations if record.get("status", "PENDING_MANAGER_APPROVAL") == "PENDING_MANAGER_APPROVAL")
    return DashboardMetrics(
        inventory_risk_items=sum(1 for item in inventory if item.get("status") == "reorder_recommended"),
        pending_interventions=pending,
        total_waste_week_kg=round(recent_kg, 2),
        waste_trend_percentage=round(trend, 1),
        financial_loss_week_inr=round(sum(float(record.get("financial_loss_inr", 0)) for record in recent_waste), 2),
        donation_handovers=len(handovers),
    )

@router.get("/waste-trend", response_model=List[WasteTrendPoint])
def get_waste_trend(restaurant_id: str = Depends(get_restaurant_id)):
    records = db.get_collection(f"restaurants/{restaurant_id}/waste_records")
    today = datetime.now(timezone.utc).date()
    totals = {}
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        totals[day] = 0.0
    for record in records:
        raw_date = record.get("date") or record.get("created_at")
        try:
            record_day = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00")).date()
        except (TypeError, ValueError):
            try:
                record_day = date.fromisoformat(str(raw_date)[:10])
            except (TypeError, ValueError):
                continue
        if record_day in totals:
            quantity = float(record.get("quantity", 0))
            unit = str(record.get("unit", "")).strip().lower()
            if unit in {"kg", "kilogram", "kilograms"}:
                totals[record_day] += quantity
            elif unit in {"g", "gm", "grm", "gram", "grams"}:
                totals[record_day] += quantity / 1000
    return [WasteTrendPoint(day=day.strftime("%a"), waste=round(value, 3)) for day, value in totals.items()]
