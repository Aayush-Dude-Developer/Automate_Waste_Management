import uuid
from datetime import datetime, timezone
from typing import List, Optional
from ..repositories.database import db
from ..schemas.inventory import InventoryItemCreate, InventoryItemResponse, StockMovementCreate, StockMovementResponse

def create_inventory_item(restaurant_id: str, item: InventoryItemCreate) -> InventoryItemResponse:
    item_id = f"inv_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    doc_data = item.model_dump()
    doc_data.update({
        "id": item_id,
        "restaurant_id": restaurant_id,
        "total_current_quantity": item.current_quantity_in_store + item.current_quantity_in_use,
        "status": "reorder_recommended" if item.current_quantity_in_store + item.current_quantity_in_use <= item.reorder_threshold else "in_stock",
        "updated_at": now.isoformat()
    })
    
    collection_path = f"restaurants/{restaurant_id}/inventory_items"
    db.add_document(collection_path, item_id, doc_data)
    
    return InventoryItemResponse(**doc_data)

def get_inventory_items(restaurant_id: str) -> List[InventoryItemResponse]:
    collection_path = f"restaurants/{restaurant_id}/inventory_items"
    docs = db.get_collection(collection_path)
    return [InventoryItemResponse(**doc) for doc in docs]

def get_inventory_item(restaurant_id: str, item_id: str) -> Optional[InventoryItemResponse]:
    collection_path = f"restaurants/{restaurant_id}/inventory_items"
    doc = db.get_document(collection_path, item_id)
    if doc:
        return InventoryItemResponse(**doc)
    return None

def record_stock_movement(restaurant_id: str, movement: StockMovementCreate, user: str) -> StockMovementResponse:
    movement_id = f"mov_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Fetch current item to update balance
    item = get_inventory_item(restaurant_id, movement.item_id)
    if not item:
        raise ValueError(f"Inventory item {movement.item_id} not found")
        
    balance_after = item.total_current_quantity + movement.quantity_delta
    if balance_after < 0:
        raise ValueError("Stock movement would make inventory quantity negative.")
    
    doc_data = movement.model_dump()
    doc_data.update({
        "id": movement_id,
        "restaurant_id": restaurant_id,
        "timestamp": now.isoformat(),
        "balance_after": balance_after,
        "created_by": user
    })
    
    mov_collection_path = f"restaurants/{restaurant_id}/stock_movements"
    db.add_document(mov_collection_path, movement_id, doc_data)
    
    # Update inventory balance
    inv_collection_path = f"restaurants/{restaurant_id}/inventory_items"
    
    # Simplistic update for now: assuming delta goes to/from in_use
    new_in_use = item.current_quantity_in_use + movement.quantity_delta
    
    updated_item_data = item.model_dump()
    # Pydantic v2 dump includes datetime objects, need to format them for JSON/Firestore
    updated_item_data["updated_at"] = now.isoformat()
    updated_item_data["current_quantity_in_use"] = new_in_use
    updated_item_data["total_current_quantity"] = balance_after
    
    if balance_after <= item.reorder_threshold:
        updated_item_data["status"] = "reorder_recommended"
    else:
        updated_item_data["status"] = "in_stock"
        
    db.add_document(inv_collection_path, item.id, updated_item_data)
    
    return StockMovementResponse(**doc_data)
