from fastapi import APIRouter, Header
from typing import List
from ..schemas.waste import WasteRecordCreate, WasteRecordResponse, StaffMealRecordCreate, StaffMealRecordResponse
from ..services import waste_service

router = APIRouter(tags=["Wastage & Staff Meals"])

@router.post("/api/waste", response_model=WasteRecordResponse)
def log_waste(waste: WasteRecordCreate, x_restaurant_id: str = Header(default="taiken_kharadi")):
    return waste_service.log_waste_record(x_restaurant_id, waste)

@router.get("/api/waste", response_model=List[WasteRecordResponse])
def get_waste(x_restaurant_id: str = Header(default="taiken_kharadi")):
    return waste_service.get_waste_records(x_restaurant_id)

@router.post("/api/staff-meals", response_model=StaffMealRecordResponse)
def log_staff_meal(meal: StaffMealRecordCreate, x_restaurant_id: str = Header(default="taiken_kharadi")):
    return waste_service.log_staff_meal(x_restaurant_id, meal)

@router.get("/api/staff-meals", response_model=List[StaffMealRecordResponse])
def get_staff_meals(x_restaurant_id: str = Header(default="taiken_kharadi")):
    return waste_service.get_staff_meal_records(x_restaurant_id)
