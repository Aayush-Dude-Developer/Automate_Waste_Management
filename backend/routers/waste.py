from fastapi import APIRouter, Depends, Query
from typing import List
from ..auth import get_restaurant_id
from ..schemas.waste import WasteRecordCreate, WasteRecordResponse, StaffMealRecordCreate, StaffMealRecordResponse
from ..services import waste_service

router = APIRouter(tags=["Wastage & Staff Meals"])

@router.post("/api/waste", response_model=WasteRecordResponse)
def log_waste(waste: WasteRecordCreate, restaurant_id: str = Depends(get_restaurant_id)):
    return waste_service.log_waste_record(restaurant_id, waste)

@router.get("/api/waste", response_model=List[WasteRecordResponse])
def get_waste(
    limit: int | None = Query(default=None, ge=1, le=500),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return waste_service.get_waste_records(restaurant_id, limit)

@router.post("/api/staff-meals", response_model=StaffMealRecordResponse)
def log_staff_meal(meal: StaffMealRecordCreate, restaurant_id: str = Depends(get_restaurant_id)):
    return waste_service.log_staff_meal(restaurant_id, meal)

@router.get("/api/staff-meals", response_model=List[StaffMealRecordResponse])
def get_staff_meals(
    limit: int | None = Query(default=None, ge=1, le=500),
    restaurant_id: str = Depends(get_restaurant_id),
):
    return waste_service.get_staff_meal_records(restaurant_id, limit)
