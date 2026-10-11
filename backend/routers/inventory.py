from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..auth import get_restaurant_id
from ..schemas.inventory import InventoryItemCreate, InventoryItemResponse, StockMovementCreate, StockMovementResponse
from ..services import inventory_service

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

@router.post("/items", response_model=InventoryItemResponse)
def create_item(item: InventoryItemCreate, restaurant_id: str = Depends(get_restaurant_id)):
    return inventory_service.create_inventory_item(restaurant_id, item)

@router.get("/items", response_model=List[InventoryItemResponse])
def get_items(restaurant_id: str = Depends(get_restaurant_id)):
    return inventory_service.get_inventory_items(restaurant_id)

@router.post("/movements", response_model=StockMovementResponse)
def add_movement(movement: StockMovementCreate, restaurant_id: str = Depends(get_restaurant_id)):
    try:
        return inventory_service.record_stock_movement(restaurant_id, movement, user="api_user")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
