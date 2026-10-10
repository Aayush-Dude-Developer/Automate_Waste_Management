import uuid
from datetime import datetime, timezone
from typing import List
from ..repositories.database import db
from ..schemas.waste import WasteRecordCreate, WasteRecordResponse, StaffMealRecordCreate, StaffMealRecordResponse
from ..schemas.inventory import StockMovementCreate
from .inventory_service import get_inventory_item, record_stock_movement

def log_waste_record(restaurant_id: str, waste: WasteRecordCreate) -> WasteRecordResponse:
    waste_id = f"wst_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    financial_loss_inr = 0.0
    
    # If linked to inventory, calculate loss and deduct stock
    if waste.inventory_item_id:
        item = get_inventory_item(restaurant_id, waste.inventory_item_id)
        if item:
            financial_loss_inr = waste.quantity * item.unit_cost_inr
            # Automatically create a negative stock movement
            movement = StockMovementCreate(
                item_id=waste.inventory_item_id,
                movement_type="WASTE_RECORDED",
                quantity_delta=-abs(waste.quantity),
                unit=waste.unit,
                reference_id=waste_id,
                notes=f"Waste: {waste.reason}"
            )
            record_stock_movement(restaurant_id, movement, user=waste.checked_by)
            
    doc_data = waste.model_dump()
    doc_data.update({
        "id": waste_id,
        "restaurant_id": restaurant_id,
        "financial_loss_inr": financial_loss_inr,
        "status": "VERIFIED",
        "created_at": now.isoformat()
    })
    
    collection_path = f"restaurants/{restaurant_id}/waste_records"
    db.add_document(collection_path, waste_id, doc_data)
    
    return WasteRecordResponse(**doc_data)

def log_staff_meal(restaurant_id: str, meal: StaffMealRecordCreate) -> StaffMealRecordResponse:
    meal_id = f"sml_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    total_cost_inr = 0.0
    
    # Process each ingredient used in the staff meal
    for ingredient in meal.items:
        if ingredient.inventory_item_id:
            item = get_inventory_item(restaurant_id, ingredient.inventory_item_id)
            if item:
                total_cost_inr += ingredient.quantity * item.unit_cost_inr
                
                # Automatically create a negative stock movement
                movement = StockMovementCreate(
                    item_id=ingredient.inventory_item_id,
                    movement_type="USAGE_STAFF_MEAL",
                    quantity_delta=-abs(ingredient.quantity),
                    unit=ingredient.unit,
                    reference_id=meal_id,
                    notes=f"Staff Meal ({meal.shift})"
                )
                record_stock_movement(restaurant_id, movement, user=meal.verified_by_duty_manager)

    doc_data = meal.model_dump()
    doc_data.update({
        "id": meal_id,
        "restaurant_id": restaurant_id,
        "total_cost_inr": total_cost_inr,
        "deducted_from_inventory": True,
        "created_at": now.isoformat()
    })
    
    collection_path = f"restaurants/{restaurant_id}/staff_meal_records"
    db.add_document(collection_path, meal_id, doc_data)
    
    return StaffMealRecordResponse(**doc_data)

def get_waste_records(restaurant_id: str) -> List[WasteRecordResponse]:
    collection_path = f"restaurants/{restaurant_id}/waste_records"
    docs = db.get_collection(collection_path)
    return [WasteRecordResponse(**doc) for doc in docs]

def get_staff_meal_records(restaurant_id: str) -> List[StaffMealRecordResponse]:
    collection_path = f"restaurants/{restaurant_id}/staff_meal_records"
    docs = db.get_collection(collection_path)
    return [StaffMealRecordResponse(**doc) for doc in docs]
