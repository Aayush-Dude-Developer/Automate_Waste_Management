from fastapi import APIRouter, Header
from typing import List
from ..schemas.inventory import InventoryItemCreate, InventoryItemResponse, StockMovementCreate, StockMovementResponse
from ..services import inventory_service

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

@router.post("/items", response_model=InventoryItemResponse)
def create_item(item: InventoryItemCreate, x_restaurant_id: str = Header(default="taiken_kharadi")):
    return inventory_service.create_inventory_item(x_restaurant_id, item)

@router.get("/items", response_model=List[InventoryItemResponse])
def get_items(x_restaurant_id: str = Header(default="taiken_kharadi")):
    return inventory_service.get_inventory_items(x_restaurant_id)

@router.post("/movements", response_model=StockMovementResponse)
def add_movement(movement: StockMovementCreate, x_restaurant_id: str = Header(default="taiken_kharadi")):
    return inventory_service.record_stock_movement(x_restaurant_id, movement, user="api_user")
